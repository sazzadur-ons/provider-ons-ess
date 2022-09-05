#!/usr/bin/env python
# coding: utf-8

# In[49]:


from gssutils import *
from datetime import date
import json


# In[50]:


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

def diff_month(d1, d2):
    return (d1.year - d2.year) * 12 + d1.month - d2.month


# In[51]:


scraper = Scraper(seed="info.json")
scraper


# In[52]:


for i in scraper.distributions:
    print(i.title)
    if 'annual data tables' in i.title:
        dist = i


# In[53]:


tabs = [tab for tab in dist.as_databaker() if 'Table' in tab.name]

for i in tabs:
    print(i.name)


# In[54]:


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

    periodRange = diff_month(b, a)

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
    savepreviewhtml(tidy_sheet, fname='previews/' + tab.name + " Preview.html")

    df = tidy_sheet.topandas()

    tidied_sheets.append(df)

df


# In[55]:


df = pd.concat(tidied_sheets).fillna('')

df = df.replace({'DATAMARKER' : {'x' : 'suppressed'},
                 'Lower Estimate' : {'x' : ''},
                 'Upper Estimate' : {'x' : ''},
                 'No. of Respondents' : {'x' : ''}})

df = df.rename(columns={'DATAMARKER' : 'Marker', 'OBS' : 'Value'})

df['Response'] = df.apply(lambda x: x['Question'].split(' - ')[1] + ' - ' + x['Response'] if 'Ethnicity' in x['Question'] else x['Response'], axis = 1)

df['Question'] = df.apply(lambda x: x['Question'].split(' - ')[0]if 'Ethnicity' in x['Question'] else x['Question'], axis = 1)

df['Question'] = df.apply(lambda x: 'Region' if 'Region' in x['Question'] else x['Question'], axis = 1)

df['Period'] = df.apply(lambda x: 'gregorian-interval/' + x['Period'].split()[1] + '-' + x['Period'].split()[0] + '-' + '01' + 'T00:00:00/P' + str(x['Period Range']) + 'M', axis = 1)

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

df = df[['Period', 'Survey Topic', 'Question', 'Response', 'Value', 'Lower Estimate', 'Upper Estimate', 'No. of Respondents', 'Base', 'Marker']]#, 'TabName']]#, 'Measure Type', 'Unit']]

df = df.rename(columns= {'Response' : 'Response Breakdown'})

df


# In[56]:


info = open('info.json')
  
data = json.load(info)

info.close()

data


# In[57]:


for i in df['Survey Topic'].unique().tolist():
    frame = df[ df['Survey Topic'] == i ]
    frame = frame.drop(columns=['Survey Topic'])

    scraper.dataset.title = i
    frame.to_csv(pathify(i.replace('/', '-')) + '-observations.csv', index=False)

    catalog_metadata = scraper.as_csvqb_catalog_metadata()
    catalog_metadata.to_json_file(pathify(i.replace('/', '-')) + '-catalog-metadata.json')

    with open(pathify(i.replace('/', '-')) + "-info.json", "w") as outfile:
        json.dump(data, outfile)


# In[58]:


from IPython.core.display import HTML
for col in df:
    if col not in ['Value']:
        df[col] = df[col].astype('category')
        display(HTML(f"<h2>{col}</h2>"))
        display(df[col].cat.categories)

