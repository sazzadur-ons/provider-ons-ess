#!/usr/bin/env python
# coding: utf-8

# In[18]:


from gssutils import *
from datetime import date
import json


# In[19]:


def cell_to_string(cell):
    s = str(cell)
    if s.find("'") > 10:
        start = s.find('"') + len('"')
        end = s.find(">")
        substring = s[start:end].strip('"')
    else:
        start = s.find("'") + len("'")
        end = s.find(">")
        substring = s[start:end].strip("'")
    return substring

months = {'January' : '01', 
          'February' : '02', 
          'March'    : '03',
          'April'    : '04',
          'May'      : '05',
          'June'     : '06',
          'July'     : '07',
          'August'   : '08',
          'September': '09',
          'October'  : '10',
          'November' : '11',
          'December' : '12'}


# In[20]:


scraper = Scraper(seed="info.json")
scraper


# In[21]:


for i in scraper.distributions:
    print(i.title)
    if 'annual data tables' in i.title:
        dist = i


# In[22]:


tabs = [tab for tab in dist.as_databaker() if 'Table' in tab.name]

for i in tabs:
    print(i.name)


# In[23]:


tidied_sheets = []

for tab in tabs:

    print(tab.name)

    pivot = tab.filter('Question')

    
    period = cell_to_string(tab.excel_ref("A1")).split(',')[1]
    
    for word, number in months.items():
        period = period.strip().replace(word, number)

    periodRange = period.split()

    periodRange = [int(i) for i in periodRange if i.isnumeric() == True]

    a = date(periodRange[1],periodRange[0],1)
    b = date(periodRange[3],periodRange[2],31)

    # Sheets only specify months, has been assumed to be start of first month to end of second

    periodRange = -(a-b).days

    topic = cell_to_string(tab.excel_ref("A1")).split(',')[0].split(':')[1].strip()

    question = pivot.fill(DOWN).is_not_blank()
        
    response = pivot.shift(RIGHT).fill(DOWN).is_not_blank()

    measure = pivot.shift(2, 0).expand(RIGHT).is_not_blank()

    lower_es = tab.filter(contains_string('Lower estimate')).fill(DOWN).is_not_blank()

    upper_es = tab.filter(contains_string('Upper estimate')).fill(DOWN).is_not_blank()

    respondents = upper_es.shift(RIGHT)

    base = respondents.shift(RIGHT)

    observations = lower_es.shift(LEFT)

    dimensions = [
        HDimConst('Period', period),
        HDimConst('Period Range', periodRange),
        HDimConst('Survey Topic', topic),
        HDim(question, 'Question', DIRECTLY, LEFT),
        HDim(response, 'Response', DIRECTLY, LEFT),
        HDim(measure, 'Measure Type', DIRECTLY, ABOVE),
        HDim(lower_es, 'Lower Estimate', DIRECTLY, RIGHT),
        HDim(upper_es, 'Upper Estimate', DIRECTLY, RIGHT),
        HDim(respondents, 'No. of Respondents', DIRECTLY, RIGHT),
        HDim(base, 'Base', DIRECTLY, RIGHT),
        HDimConst('TabName', tab.name.replace('Table', ''))
        ]

    tidy_sheet = ConversionSegment(tab, dimensions, observations)
    savepreviewhtml(tidy_sheet, fname=tab.name + " Preview.html")

    df = tidy_sheet.topandas()

    tidied_sheets.append(df)

df


# In[24]:


import numpy as np

df = pd.concat(tidied_sheets).fillna('')

df = df.replace({'Lower Estimate' : {'x' : ''},
                 'Upper Estimate' : {'x' : ''},
                 'No. of Respondents' : {'x' : ''}})

df['DATAMARKER'] = df.apply(lambda x: 'suppressed' if 'x' in x['DATAMARKER'] else np.nan, axis = 1)

df = df.rename(columns={'DATAMARKER' : 'Marker', 'OBS' : 'Value'})

df['Response'] = df.apply(lambda x: x['Question'].split(' - ')[1] + ' - ' + x['Response'] if 'Ethnicity' in x['Question'] else x['Response'], axis = 1)

df['Question'] = df.apply(lambda x: x['Question'].split(' - ')[0]if 'Ethnicity' in x['Question'] else x['Question'], axis = 1)

df['Region Temp'] = df['Question']

df['Question'] = df.apply(lambda x: 'Region' if 'Region' in x['Question'] else x['Question'], axis = 1)

df['Period'] = df.apply(lambda x: 'gregorian-interval/' + x['Period'].split()[1] + '-' + x['Period'].split()[0] + '-' + '31' + 'T00:00:00/P' + str(x['Period Range']) + 'D', axis = 1)

df['Value'] = df.apply(lambda x: 0 if 'suppressed' in str(x['Marker']) else x['Value'], axis = 1)
df['Lower Estimate'] = df.apply(lambda x: 0 if 'suppressed' in str(x['Marker']) else x['Lower Estimate'], axis = 1)
df['Upper Estimate'] = df.apply(lambda x: 0 if 'suppressed' in str(x['Marker']) else x['Upper Estimate'], axis = 1)
df['No. of Respondents'] = df.apply(lambda x: 0 if 'suppressed' in str(x['Marker']) else x['No. of Respondents'], axis = 1)

ROUNDCOL = ['Value', 'Lower Estimate', 'Upper Estimate']

for col in df.columns.values.tolist():
	if col in ROUNDCOL:
		df[col] = df[col].apply(lambda x: round(float(x), 2))

df['Response'] = df['Response'].str.replace('\[Note 4\]', '').str.strip()

df['Measure Type'] = 'percentage-of-respondents'
df['Unit'] = 'percent'

df['Base'] = df['Base'].astype(float).astype(int)
df['No. of Respondents'] = df['No. of Respondents'].astype(float).astype(int)

df = df.replace({'Question' : {'Reasons for visiting ' : 'Reasons for Visiting', 'Reasons for visiting' : 'Reasons for Visiting',
                               'Taken a holiday in England in the last 12 months ' : 'Taken a holiday in England in the last 12 months'}})

df['Response'] = df['Response'].str.replace(r"[\"\'\’,]", "'")

df['Response'] = df['Response'].apply(pathify)

df = df[['Period', 'Survey Topic', 'Question', 'Region Temp', 'Response', 'Value', 'Lower Estimate', 'Upper Estimate', 'No. of Respondents', 'Base', 'Marker', 'TabName']]#, 'Measure Type', 'Unit']]

df


# In[25]:


from IPython.core.display import HTML
for col in df:
    if col not in ['Value']:
        df[col] = df[col].astype('category')
        display(HTML(f"<h2>{col}</h2>"))
        display(df[col].cat.categories)


# In[26]:


sepDf = df[ df['TabName'].str.contains('1b|1d|2b|2d|3b|3d|4b|5b|6b|7b|7c|7d|7e|8a|8d|8e|8f|8g|8h') ]

sepDf = sepDf.drop(columns=['TabName'])

sepFrames = {}

for i in sepDf['Question'].unique().tolist():
    frame = sepDf[ sepDf['Question'] == i]

    frame['Survey Topic'] = frame['Survey Topic'].apply(pathify)

    if 'region' in pathify(i):
        frame['Response'] = frame.apply(lambda x: pathify(x['Region Temp']) + '-' + x['Response'] if 'ITL' in x['Region Temp'] else x['Response'], axis = 1)
        
    frame = frame.drop(columns=['Question', 'Region Temp'])

    info = open('info.json')

    data = json.load(info)

    data['transform']['columns'].pop('Question')

    if 'suppressed' not in frame.values:
        frame = frame.drop(columns=['Marker'])
        data['transform']['columns'].pop('Marker')

    scraper.dataset.title = "Participation Survey by " + i.replace('/', '-')

    frame.to_csv(pathify(i.replace('/', '-')) + '-observations.csv', index=False)

    catalog_metadata = scraper.as_csvqb_catalog_metadata()
    catalog_metadata.title = scraper.dataset.title
    catalog_metadata.to_json_file(pathify(i.replace('/', '-')) + '-catalog-metadata.json')

    info.close()

    with open(pathify(i.replace('/', '-')) + "-info.json", "w") as outfile:
        json.dump(data, outfile, indent=4)


#sepDf.to_csv('Question-observations.csv', index=False)
#catalog_metadata = scraper.as_csvqb_catalog_metadata()
#catalog_metadata.to_json_file('Question-catalog-metadata.json')

frame


# In[27]:


sepDf = df[ ~df['TabName'].str.contains('1b|1d|2b|2d|3b|3d|4b|5b|6b|7b|7c|7d|7e|8a|8d|8e|8f|8g|8h') ]

sepDf = sepDf.drop(columns=['TabName'])

sepFrames = {}

for i in sepDf['Survey Topic'].unique().tolist():
    frame = sepDf[ sepDf['Survey Topic'] == i ]

    frame['Question'] = frame['Question'].apply(pathify)

    frame = frame.drop(columns=['Survey Topic', 'Region Temp'])

    info = open('info.json')

    data = json.load(info)

    data['transform']['columns'].pop('Survey Topic')

    if 'suppressed' not in frame.values:
        frame = frame.drop(columns=['Marker'])
        data['transform']['columns'].pop('Marker')

    if 'adults-use-of-the-internet-smart-devices' in pathify(i):
        indexNames = frame[ frame['Response'] == 'none-of-these' ].index
        frame.drop(indexNames, inplace = True)

        #if this isnt fixed in the next release fix this properly

    scraper.dataset.title = "Participation Survey by " + i.replace('/', '-')

    if scraper.dataset.title == 'Participation Survey by Adults engagement with tourism in the last 12 months (physical)':
        
        df = df.replace({'Response' : {'2021-06-03' : '3-6', '2021-10-07' : '7-10'}})

    
    frame.to_csv(pathify(i.replace('/', '-')) + '-observations.csv', index=False)

    catalog_metadata = scraper.as_csvqb_catalog_metadata()
    catalog_metadata.title = scraper.dataset.title
    catalog_metadata.to_json_file(pathify(i.replace('/', '-')) + '-catalog-metadata.json')

    info.close()

    with open(pathify(i.replace('/', '-')) + "-info.json", "w") as outfile:
        json.dump(data, outfile, indent=4)

#sepDf.to_csv('Survey-observations.csv', index=False)
#catalog_metadata = scraper.as_csvqb_catalog_metadata()
#catalog_metadata.to_json_file('Survey-catalog-metadata.json')

frame


# In[ ]:





# In[28]:


"""1b 1d 2b 2d 3b 3d 4b 5b 6b 7b 7c 7d 7e 8a 8d 8e 8f 8g 8h"""

