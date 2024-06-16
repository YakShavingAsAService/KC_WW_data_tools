import os
import pandas as pd
import IPython

# the file name that this script will ingest
csv_output_fname = "kcww.csv"
(fname,ext) = os.path.splitext(csv_output_fname)

# read in the csv that kc_ww_data.py made
wwdf = pd.read_csv(csv_output_fname, sep='\t')

# add column headers
wwdf.columns = ['Site Name', 'Sample Collection Date', 'Concentration' ]

# for every site in the csv ...
site_names = wwdf['Site Name'].unique()
for s in site_names:

   # ... grab all the rows in the original csv file for that site
   site_df = wwdf.loc[ wwdf['Site Name'] == s].copy(deep=True)

   # turn the sample collection date column into a datetime object ...
   datetime_series = pd.to_datetime(site_df['Sample Collection Date'])
   # ... so we can identify missing rows
   site_start = datetime_series.iloc[0]
   site_end = datetime_series.iloc[-1]
   diff = pd.date_range(start = site_start, end = site_end).difference( datetime_series )

   # report out some statistics about this site
   print("Site %s has %d rows" % (s,len(site_df)))
   print("Site %s missing these timestamps:" % (s))
   for d in diff: print("\t%s" % d)

   # build a 7DRA column. Do two versions, centered and not centered, and write them as csvs
   ra_not_centered_fname = "%s_%s%s%s" % (fname,s,"_plus_7dra_not_centered",ext)
   ra_centered_fname = "%s_%s%s%s" % (fname,s,"_plus_7dra_centered",ext)

   not_centered_site_df = site_df.copy(deep=True)
   not_centered_site_df['7dra_not_centered'] = not_centered_site_df['Concentration'].rolling(window=7,center=False).mean()
   not_centered_site_df.to_csv(path_or_buf=ra_not_centered_fname, index = False)

   print("stored %d records for %s to %s" % (len(site_df),s,ra_not_centered_fname))

   centered_site_df = site_df.copy(deep=True)
   centered_site_df['7dra_centered'] = centered_site_df['Concentration'].rolling(window=7,center=True).mean()
   centered_site_df.to_csv(path_or_buf=ra_centered_fname, index = False)

   print("stored %d records for %s to %s" % (len(site_df),s,ra_centered_fname))


