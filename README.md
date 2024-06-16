# KC_WW_data_tools
Tools to collect and process Sars-CoV-2 wastewater data from the King County, WA, Covid dashboard, located at https://kingcounty.gov/en/dept/dph/health-safety/disease-illness/facts-and-data/respiratory-virus-data

## Tools in the repo
The main tool in this repo is kc_ww_data.py, which is a python3/selenium script that picks up the tooltip data (catchment name, sample date, normalized Sars-Cov-2 concentrations) in the Tableau visualization for the three King County wastewater sites and turns them into a csv file. I wrote this because there's no way (at present) to download the data. This will take 30 or 40 minutes to run, and it will store the results in a file in the same folder called kcww.csv. There's an example output in 20240615_output.

The next tool is create_per_site_csv.py. It ingests the file producted by kc_ww_data.py and produces a per-site .csv file. It will add two 7DRA columns, one centered and one not. It will also report some statistics about how many rows each per-site csv has, and note any missing rows, based on the date. Example outputs are also in 20240615_output. To run this script you need the pandas module in python, which you can install via pip or the equivalent of your choice.

## What do the concentration numbers actually mean?
This is an excellent question! Sadly, I do not have an excellent answer to give you in return.

The county's webpage says sampling is done twice a week at each plant. But ... the data series show entries for nearly every day. And the entries are different! This implies that samples are done more often than twice a week. The page also says the results are normalized, but doesn't give more details. Presumably it is trying to adjust for things for things like rainwater dilution.

## Run this code
The kc_ww_data.py python3 script uses the Selenium modules with the Chromedriver tool. Any recent version of Python3 will work. Use pip (or the equivalent of your choice) to install Selenium; you can find out more information about Selenium here: https://www.selenium.dev/. You can download Chromedriver here: https://googlechromelabs.github.io/chrome-for-testing/. More information about Chromedriver is available here: https://developer.chrome.com/docs/chromedriver/downloads.

The create_per_site_csv.py python3 script uses the pandas modile. Use pip (or the equivalent tool) to install. You can find out more about pandas here: https://pandas.pydata.org/.

## License
These tools are licensed under the MIT license.
