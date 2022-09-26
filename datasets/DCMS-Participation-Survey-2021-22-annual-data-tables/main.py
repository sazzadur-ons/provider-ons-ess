#!/usr/bin/env python
# coding: utf-8

# In[92]:


from gssutils import *
from datetime import date
import json


# In[93]:


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


# In[94]:


scraper = Scraper(seed="info.json")
scraper


# In[95]:


for i in scraper.distributions:
    print(i.title)
    if 'annual data tables' in i.title:
        dist = i


# In[96]:


tabs = [tab for tab in dist.as_databaker() if 'Table' in tab.name]

for i in tabs:
    print(i.name)


# In[97]:


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


# In[98]:


df = pd.concat(tidied_sheets).fillna('')

df = df.replace({'DATAMARKER' : {'x' : 'suppressed'},
                 'Lower Estimate' : {'x' : ''},
                 'Upper Estimate' : {'x' : ''},
                 'No. of Respondents' : {'x' : ''}})

df = df.rename(columns={'DATAMARKER' : 'Marker', 'OBS' : 'Value'})

df['Response'] = df.apply(lambda x: x['Question'].split(' - ')[1] + ' - ' + x['Response'] if 'Ethnicity' in x['Question'] else x['Response'], axis = 1)

df['Question'] = df.apply(lambda x: x['Question'].split(' - ')[0]if 'Ethnicity' in x['Question'] else x['Question'], axis = 1)

df['Question'] = df.apply(lambda x: 'Region' if 'Region' in x['Question'] else x['Question'], axis = 1)

df['Period'] = df.apply(lambda x: 'gregorian-interval/' + x['Period'].split()[1] + '-' + x['Period'].split()[0] + '-' + '31' + 'T00:00:00/P' + str(x['Period Range']) + 'D', axis = 1)

df['Value'] = df.apply(lambda x: 0 if 'suppressed' in x['Marker'] else x['Value'], axis = 1)
df['Lower Estimate'] = df.apply(lambda x: 0 if 'suppressed' in x['Marker'] else x['Lower Estimate'], axis = 1)
df['Upper Estimate'] = df.apply(lambda x: 0 if 'suppressed' in x['Marker'] else x['Upper Estimate'], axis = 1)
df['No. of Respondents'] = df.apply(lambda x: 0 if 'suppressed' in x['Marker'] else x['No. of Respondents'], axis = 1)

ROUNDCOL = ['Value', 'Lower Estimate', 'Upper Estimate']

for col in df.columns.values.tolist():
	if col in ROUNDCOL:
		df[col] = df[col].apply(lambda x: round(float(x), 2))

df['Response'] = df['Response'].str.replace('\[Note 4\]', '').str.strip()

df['Measure Type'] = 'percentage-of-respondents'
df['Unit'] = 'percent'

df = df[['Period', 'Survey Topic', 'Question', 'Response', 'Value', 'Lower Estimate', 'Upper Estimate', 'No. of Respondents', 'Base', 'Marker', 'TabName']]#, 'Measure Type', 'Unit']]

df


# In[99]:


from IPython.core.display import HTML
for col in df:
    if col not in ['Value']:
        df[col] = df[col].astype('category')
        display(HTML(f"<h2>{col}</h2>"))
        display(df[col].cat.categories)


# In[100]:


info = open('info.json')
  
data = json.load(info)

info.close()

data


# In[101]:


dataQuestion = data
dataSurveyTopic = data

for i in dataQuestion['transform']['columns']:
    if dataQuestion['transform']['columns'] == 'Question':
        dataQuestion.pop(i)

for i in dataSurveyTopic['transform']['columns']:
    if dataSurveyTopic['transform']['columns'] == 'Survey Topic':
        dataSurveyTopic.pop(i)


# In[102]:


sepDf = df[ df['TabName'].str.contains('1b|1d|2b|2d|3b|3d|4b|5b|6b|7b|7c|7d|7e|8a|8d|8e|8f|8g|8h') ]

sepDf = sepDf.drop(columns=['TabName'])

sepFrames = {}

for i in sepDf['Question'].unique().tolist():
    frame = sepDf[ sepDf['Question'] == i]
    frame = frame.drop(columns=['Question'])

    scraper.dataset.title = "Participation Survey by " + i.replace('/', '-')

    frame.to_csv(pathify(i.replace('/', '-')) + '-observations.csv', index=False)

    catalog_metadata = scraper.as_csvqb_catalog_metadata()
    catalog_metadata.title = scraper.dataset.title
    catalog_metadata.to_json_file(pathify(i.replace('/', '-')) + '-catalog-metadata.json')

    with open(pathify(i.replace('/', '-')) + "-info.json", "w") as outfile:
        json.dump(data, outfile, indent=4)

frame


# In[103]:


sepDf = df[ ~df['TabName'].str.contains('1b|1d|2b|2d|3b|3d|4b|5b|6b|7b|7c|7d|7e|8a|8d|8e|8f|8g|8h') ]

sepDf = sepDf.drop(columns=['TabName'])

sepFrames = {}

for i in sepDf['Survey Topic'].unique().tolist():
    frame = sepDf[ sepDf['Survey Topic'] == i ]
    frame = frame.drop(columns=['Survey Topic'])

    scraper.dataset.title = "Participation Survey by " + i.replace('/', '-')
    
    frame.to_csv(pathify(i.replace('/', '-')) + '-observations.csv', index=False)

    catalog_metadata = scraper.as_csvqb_catalog_metadata()
    catalog_metadata.title = scraper.dataset.title
    catalog_metadata.to_json_file(pathify(i.replace('/', '-')) + '-catalog-metadata.json')

    with open(pathify(i.replace('/', '-')) + "-info.json", "w") as outfile:
        json.dump(data, outfile, indent=4)

frame


# In[104]:


#df.to_csv('observations.csv', index=False)

#catalog_metadata = scraper.as_csvqb_catalog_metadata()
#catalog_metadata.to_json_file('catalog-metadata.json')


# In[105]:


"""1b 1d 2b 2d 3b 3d 4b 5b 6b 7b 7c 7d 7e 8a 8d 8e 8f 8g 8h"""

