import csv
from datetime import datetime
import locale
import re
from selenium import webdriver
from selenium.common import exceptions as SeleniumExceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
import time

# load the tableau image at tableau_kc_ww_iframe_url and move a mouse over it to capture tooltip data

tableau_kc_ww_iframe_url = "https://tableaupub.kingcounty.gov/t/Public/views/Influenzaandotherrespiratorydiseases/COVIDWastewater?%3Aembed=y&%3AisGuestRedirectFromVizportal=y"
kc_ww_url = 'https://kingcounty.gov/en/dept/dph/health-safety/disease-illness/facts-and-data/respiratory-virus-data'
csv_output_file_name = 'kcww.csv'
tooltip_re = 'Catchment:\s*(\S+)\nDate:\s*(\S+)\nSARS-CoV-2 wastewater concentration:\s*(\S+)'

# inject a mouse position marker into the page
# so we know where we are
cursor_script = '''
var cursor = document.createElement('div');
cursor.style.position = 'absolute';
cursor.style.zIndex = '9999';
cursor.style.width = '4px';
cursor.style.height = '4px';
cursor.style.borderRadius = '50%';
cursor.style.backgroundColor = 'red';
cursor.style.pointerEvents = 'none';
document.body.appendChild(cursor);

document.addEventListener('mousemove', function(e) {
  cursor.style.left = e.pageX - 5 + 'px';
  cursor.style.top = e.pageY - 5 + 'px';
});
'''

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

def load_page(driver):
   canvas_ele = None

   # load the page
   # page is at kc_ww_url, but the viz is actually at tableau_kc_ww_iframe_url and pulled in via an iframe
   driver.get(tableau_kc_ww_iframe_url)

   try:
         # !!! brittle code alert !!!: there are multiple canvas objects in this page, and
         # they don't have nice unique ids we can use to find the one we're interested in.
         # for now just look for the 6th canvas object -- but this is prone to break the
         # next time the devs change the page layout. :(
         canvas_ele = WebDriverWait(driver,30).until(
            EC.presence_of_element_located((By.XPATH,"(//canvas)[5]"))
         )
   except SeleniumExceptions.TimeoutException as e:
      print("DOM element never found. Quitting.")
      driver.quit()
      sys.exit(1)

   # run some javascript to make the mouse cursor visible, as a debugging aid
   driver.execute_script(cursor_script)

   return canvas_ele

def trans_ul_to_c(pos, w, h):
   '''build a function that takes coordinates based on the upper left as the origin
   and translates them into coordinates based on the center as the origin.''' 
   x_inset = 0
   y_inset = 10
   x = pos[1] - (w / 2) + x_inset
   y = pos[0] - (h / 2) + y_inset
   return (x,y)

def get_offsets( pos1, pos2 ):
   '''we are at absolute position pos1 and want to move to pos2. what are the
     offsets to use?'''
   return ( pos2[0] - pos1[0], pos2[1] - pos1[1] )

def init_mouse_cursor(driver, canvas_ele, start_pos = (0,0) ):
   '''move the mouse cursor to a given location of the canvas element. The location
      assumes the upper left hand corner of the element is the origin. Position
      default is 0,0'''

   # get canvas object's size attributes
   rowheight = int(canvas_ele.size['height'])
   rowwidth = int(canvas_ele.size['width'])

   print("init mouse cursor to width %d, height: %d" % (start_pos[0], start_pos[1] ))

   # step 1: move cursor to center of canvas element
   ActionChains(driver).move_to_element(canvas_ele).pause(1.0).perform()
   print("moved mouse cursor to center")
   # step 2: figure out the correct offsets to move from center to the desired position
   (ulx,uly) = trans_ul_to_c( start_pos, w = rowwidth, h = rowheight )
   # step 3: move the cursor to the desired position
   try:
      ActionChains(driver).move_by_offset(ulx, uly).perform()
      print("moved mouse cursor by offset %d,%d" % (ulx,uly))
   except SeleniumExceptions.MoveTargetOutOfBoundsException as e:
      print("ugh, something wrong with the cursor calculations: %s" % e)
      driver.quit()

def build_work_queue(canvas_ele):
   '''we want to move the cursor to look for tooltips at every xinc pixels on every yinc rows. 
      build an array of tuples that does this given the canvas object's dimensions. Tuples will
      be absolute values with an upper left hand corner origin'''

   # column, row increment sizes
   xinc = 2 
   yinc = 4 

   # results is an array of tuples that describe absolute x,y values for pixels to
   # sample, relative to an upper left hand corner origin
   results = []

   # initialize row counter
   rowidx = 0

   # make sure we don't go out of bounds
   max_width = canvas_ele.size['width'] - xinc
   max_height = canvas_ele.size['height'] - yinc
   print("canvas element is %d pixels wide and %d pixels high" % (max_width,max_height))

   # while we have at least one row left to look at ...
   while rowidx <= max_height:

      # ... yes, but do i need to output for this particular row?
      if rowidx % yinc == 0:

         # yes! build a row ...
         row = [ (i,rowidx) for i in range(max_width+1) if i % xinc == 0 ]
         # ... then reset the column back to the leftmost column for the next row ...
         row_reset = row[0]
         row.append( row_reset )
         # ... then advance to the next row
         next_row = (0, rowidx+yinc)
         row.append( next_row )

         # add new row to results
         results += row

      rowidx += 1

   return results

def parse_tooltip_data(inputstr):
   '''turn the text of the tooltip into a dictionary.'''
   p = re.compile(tooltip_re)
   m = p.match(inputstr)
   if not m:
      raise Exception("Could not parse this tooltip? %s" % inputstr)
   else:
      # turn the date test into a datetime object so we can sort it later
      d = datetime.strptime(m.group(2),'%m/%d/%Y')
      return { 'catchment': m.group(1), 'date': d, 'concentration': locale.atoi(m.group(3)) }

def build_csv_file(results):
   '''take the results dictionary of dictionaries and turn it into a csv file'''
   with open(csv_output_file_name, 'w' ) as csvfile:
      outputwriter = csv.writer(csvfile, dialect=csv.excel_tab)

      # for each catchment site ...
      for k in results.keys():
         # ... sort the records by date ...
         sorted_items = sorted(results[k].keys())
         for s in sorted_items:
            # ... write a row per key/key/value
            dstr = s.strftime('%m/%d/%Y')
            outputwriter.writerow([k,dstr,results[k][s]])

   print("results stored in %s" % csv_output_file_name)

# instantiate chromedriver browser
chrome_options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=chrome_options)

# load page, get chart element
canvas_ele = load_page( driver )

# move the cursor to the upper left hand corner
init_mouse_cursor( driver, canvas_ele )

# build a list of positions to move the mouse to, to see if we can
# make it display a tooltip from which we can grab data
work_queue = build_work_queue(canvas_ele)

# store grabbed tooltip data in this dictionary
# tooltips_results structure: dictionary with the key being the catchment area (eg "Brightwater")
# and the value being another dictionary. The inner dictionary's key is a datetime
# object and the value is the sars-cov-2 concentration
tooltips_results = {}

# for every position ...
for wi_idx, work_item in enumerate(work_queue):

   # in selenium mouse moves are offsets from the current position, not absolute values. 
   offsets = (0,0)

   # problem: the loaded page refreshes sometimes, and when it does it causes the script 
   # to enter a zombie state. unfortunately, there's no selenium event that gets thrown 
   # that i can look at to tell when this has happened. :(
   # low-rent solution: to touch the canvas element and see if it gets me a 
   # StaleElementReferenceException. If I get one, get a new element reference,
   # reset mouse position, and continue
   try:

      cls = canvas_ele.get_attribute('class')
      #print("checking for staleness: %s" % (u'\u2713'))
      # element is not stale. get the next set of offsets to use for the mouse.
      if wi_idx > 0:
         offsets = get_offsets(work_queue[wi_idx-1],work_queue[wi_idx])

      # move the mouse cursor ...
      ActionChains(driver).move_by_offset(offsets[0], offsets[1]).perform()

      # ... and if a tooltip pops up, grab the data from it
      tooltip_eles = driver.find_elements(By.CLASS_NAME,"tab-tooltip")
      if len(tooltip_eles): 
         for t in tooltip_eles:
            print("tooltip found: %s" % t.text)
            # ... and store the data in our tooltips_results dictionary
            r = parse_tooltip_data(t.text)
            if not r['catchment'] in tooltips_results.keys(): 
               tooltips_results[r['catchment']] = { }
            # side effect of a dictionary: gets rid of dupes
            tooltips_results[r['catchment']][r['date']] = r['concentration']

   except SeleniumExceptions.StaleElementReferenceException as e:
      print("ugh, the page refreshed and send the script to zombieland. going to get element references again so i can continue.")
      canvas_ele = load_page(driver)
      init_mouse_cursor( driver, canvas_ele, work_item[wi_idx] )
      # BUG, FIXME: won't look for tooltip at work_item[wi_idx]. 
      continue
   except SeleniumExceptions.MoveTargetOutOfBoundsException as e:
      print("ugh, something wrong with the cursor calculations: %s. go fix." % e)
      driver.quit()
      sys.exit(1)
   except Exception as e:
      print("ugh, what is this? %s" % e)
      driver.quit()
      sys.exit(1)


# close the browser
print("closing the browser")
driver.quit()

# turn the tooltips_results into a csv file
print("writing results to %s ... " % csv_output_file_name, end='')
build_csv_file(tooltips_results)
print(" ... finished")



