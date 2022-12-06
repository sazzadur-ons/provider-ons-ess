#!/usr/bin/env python
# coding: utf-8

# In[123]:


from gssutils import *
from datetime import date
import json


# In[124]:


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


# In[125]:


scraper = Scraper(seed="info.json")
scraper


# In[126]:


for i in scraper.distributions:
    print(i.title)
    if 'annual data tables' in i.title:
        dist = i


# In[127]:


tabs = [tab for tab in dist.as_databaker() if 'Table' in tab.name]

for i in tabs:
    print(i.name)


# In[128]:


tidied_sheets = []

for tab in tabs:

    print(tab.name)

    pivot = tab.filter('Question')

    
    period = cell_to_string(tab.excel_ref("A1")).split(',')[1]
    
    for word, number in months.items():
        period = period.strip().replace(word, number)

    periodRange = period.split()

    #periodRange = [int(i) for i in periodRange if i.isnumeric() == True]

    #a = date(periodRange[1],periodRange[0],1)
    #b = date(periodRange[3],periodRange[2],31)

    # Sheets only specify months, has been assumed to be start of first month to end of second

    #periodRange = -(a-b).days

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
        HDim(lower_es, 'Lower Confidence Interval', DIRECTLY, RIGHT),
        HDim(upper_es, 'Upper Confidence Interval', DIRECTLY, RIGHT),
        HDim(respondents, 'No. of Respondents', DIRECTLY, RIGHT),
        HDim(base, 'Base', DIRECTLY, RIGHT),
        HDimConst('TabName', tab.name.replace('Table', ''))
        ]

    tidy_sheet = ConversionSegment(tab, dimensions, observations)
    savepreviewhtml(tidy_sheet, fname=tab.name + " Preview.html")

    df = tidy_sheet.topandas()

    tidied_sheets.append(df)

df


# In[129]:


import numpy as np

df = pd.concat(tidied_sheets).fillna('')

df = df.replace({'Lower Confidence Interval' : {'x' : ''},
                 'Upper Confidence Interval' : {'x' : ''},
                 'No. of Respondents' : {'x' : ''}})

df['DATAMARKER'] = df.apply(lambda x: 'suppressed' if 'x' in x['DATAMARKER'] else np.nan, axis = 1)

df = df.rename(columns={'DATAMARKER' : 'Marker', 'OBS' : 'Value'})

df['Response'] = df.apply(lambda x: x['Question'].split(' - ')[1] + ' - ' + x['Response'] if 'Ethnicity' in x['Question'] else x['Response'], axis = 1)

df['Question'] = df.apply(lambda x: x['Question'].split(' - ')[0]if 'Ethnicity' in x['Question'] else x['Question'], axis = 1)

df['Region Temp'] = df['Question']

df['Question'] = df.apply(lambda x: 'Region' if 'Region' in x['Question'] else x['Question'], axis = 1)

df['Period'] = df.apply(lambda x: 'government-half/' + x['Period'].split()[1] + '-' + x['Period'].split()[4] + '/h2', axis = 1)

df['Value'] = df.apply(lambda x: 0 if 'suppressed' in str(x['Marker']) else x['Value'], axis = 1)
df['Lower Confidence Interval'] = df.apply(lambda x: 0 if 'suppressed' in str(x['Marker']) else x['Lower Confidence Interval'], axis = 1)
df['Upper Confidence Interval'] = df.apply(lambda x: 0 if 'suppressed' in str(x['Marker']) else x['Upper Confidence Interval'], axis = 1)
df['No. of Respondents'] = df.apply(lambda x: 0 if 'suppressed' in str(x['Marker']) else x['No. of Respondents'], axis = 1)

ROUNDCOL = ['Value', 'Lower Confidence Interval', 'Upper Confidence Interval']

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

df = df[['Period', 'Survey Topic', 'Question', 'Region Temp', 'Response', 'Value', 'Lower Confidence Interval', 'Upper Confidence Interval', 'No. of Respondents', 'Base', 'Marker', 'TabName']]#, 'Measure Type', 'Unit']]

df


# In[130]:


from IPython.core.display import HTML
for col in df:
    if col not in ['Value']:
        df[col] = df[col].astype('category')
        display(HTML(f"<h2>{col}</h2>"))
        display(df[col].cat.categories)


# In[131]:


"""
metadata = { originalTitle : { NewTitle
                               NewDescription }}
"""

metadata = { 
"Participation Survey by Acorn" : { "Participation Survey by Socio-Economic Classification",
"The results of the Participation Survey of which relate to ACORN Eligibility (Socio-Economic Classification)."},

"Participation Survey by Adults digital skills" : { "Participation Survey by Adult's Digital Skills",
"The results of the Participation Survey relating to current Digital Skills or interest in development of Digital Skills."},

"Participation Survey by Adults engagement with heritage sites in the last 12 months (digital)" : { "Participation Survey by Adult's Engagement with Heritage Sites (Digital)",
"The results of the Participation Survey relating to Digital Engagement with Heritage Sites. "},

"Participation Survey by Adults engagement with heritage sites in the last 12 months (physical)" : { "Participation Survey by Adult's Engagement with Heritage Sites (Physical)",
"The results of the Participation Survey relating to Physical Engagement with Heritage Sites. "},

"Participation Survey by Adults engagement with libraries in the last 12 months (digital)" : { "Participation Survey by Adult's Engagement with Libraries (Digital)",
"The results of the Participation Survey relating to Digital Engagement with Libraries. "},

"Participation Survey by Adults engagement with libraries in the last 12 months (physical)" : { "Participation Survey by Adult's Engagement with Libraries (Physical)",
"The results of the Participation Survey relating to Physical Engagement with Libraries. "},

"Participation Survey by Adults engagement with live sports and gambling in the last 6-12 months (physical)" : { "Participation Survey by Adult's Engagement with Live Sports and Gambling (Physical)",
"The results of the Participation Survey relating to Physical Engagement with Live Sports and Gambling."},

"Participation Survey by Adults engagement with major events" : { "Participation Survey by Adult's Engagement with Major Events",
"The results of the Participation Survey relating to awareness and/or engagement with major events."},

"Participation Survey by Adults engagement with museums in the last 12 months (physical)" : { "Participation Survey by Adult's Engagement with Museums (Physical)",
"The results of the Participation Survey relating to Physical Engagement with Museums. "},

"Participation Survey by Adults engagement with the arts in the last 12 months (digital)" : { "Participation Survey by Adult's Engagement with the Arts (Digital)",
"The results of the Participation Survey relating to Digital Engagement with the Arts. "},

"Participation Survey by Adults engagement with the arts in the last 12 months (physical)" : { "Participation Survey by Adult's Engagement with the Arts (Physical)",
"The results of the Participation Survey relating to Physical Engagement with the Arts. "},

"Participation Survey by Adults engagement with tourism in the last 12 months (physical)" : { "Participation Survey by Adult's Engagement with Tourism (Physical)",
"The results of the Participation Survey relating to Physical Engagement with Tourism. "},

"Participation Survey by Adults knowledge of 5G" : { "Participation Survey by Adult's Knowledge of 5G",
"The results of the Participation Survey relating to Understanding and likelihood of engagement with 5G."},

"Participation Survey by Adults use of the internet (Smart Devices)" : { "Participation Survey by Adult's Use of the Internet (Smart Devices)",
"The results of the Participation Survey relating to Ownership and Usage Habits of Smart Devices."},

"Participation Survey by Age" : { "Participation Survey by Age",
"The results of the Participation Survey broken down by Age Group."},

"Participation Survey by Children living in your household" : { "Participation Survey by Children Living in Household",
"The results of the Participation Survey relating to having Children living in the Household."},

"Participation Survey by Current internet or broadband speed at home" : { "Participation Survey by Current Internet or Broadband Speed at Home",
"The results of the Participation Survey relative to one's Current internet or Broadband Speed."},

"Participation Survey by Data security" : { "Participation Survey by Data Security",
"The results of the Participation Survey relating to Understanding and Engagement with Data Security."},

"Participation Survey by Data sharing and viewing content online" : { "Participation Survey by Data Sharing and Viewing Content Online",
"The results of the Participation Survey by Online Data Sharing and Viewing Habits. "},

"Participation Survey by Digital methods of identification" : { "Participation Survey by Digital Methods of Identification",
"The results of the Participation Survey by Experience and Engagement with Digital Identification Methods."},

"Participation Survey by Employment status" : { "Participation Survey by Employment Status",
"The results of the Participation Survey by Employment Status"},

"Participation Survey by Ethnicity" : { "Participation Survey by Ethnicity",
"The results of the Participation Survey broken down by Ethnicity."},

"Participation Survey by Gender" : { "Participation Survey by Gender",
"The results of the Participation Survey broken down by Gender."},

"Participation Survey by Highest qualification" : { "Participation Survey by Highest Qualification",
"The results of the Participation Survey broken down by Highest Qualification Attained."},

"Participation Survey by Household currently pays for internet or broadband at home per month" : { "Participation Survey by Amount Household Currently Pays for Internet or Broadband at Home per Month",
"The results of the Participation Survey by Amount Household Currently Pays for Internet or Broadband at Home per Month"},

"Participation Survey by How much extra you would be willing to pay per month for 1Gbps (1000Mbps) speeds over what you currently pay" : { "Participation Survey by How much extra you would be willing to pay per month for 1Gbps (1000Mbps) speeds over what you currently pay",
"The results of the Participation Survey by How much extra you would be willing to pay per month for 1Gbps (1000Mbps) speeds over what you currently pay"},

"Participation Survey by How much extra you would be willing to pay per month to double your broadband speed" : { "Participation Survey by How much extra you would be willing to pay per month to double your broadband speed",
"The results of the Participation Survey by How much extra you would be willing to pay per month to double your broadband speed"},

"Participation Survey by Index of multiple deprivation" : { "Participation Survey by Index of Multiple Deprivation",
"The results of the Participation Survey broken down by Index of Multiple Deprivation."},

"Participation Survey by Living with someone in this household as a couple" : { "Participation Survey by Living with Someone in this Household as a Couple",
"The results of the Participation Survey broken down by whether they current live as a couple in a household."},

"Participation Survey by Long-standing illness or disability" : { "Participation Survey by Long-standing Illness or Disability",
"The results of the Participation Survey broken down by Long-standing Illness or Disability."},

"Participation Survey by NS-SEC" : { "Participation Survey by NS-SEC",
"The results of the Participation Survey broken down by NS-SEC"},

"Participation Survey by Region" : { "Participation Survey by Region",
"The results of the Participation Survey broken down by Region"},

"Participation Survey by Religion" : { "Participation Survey by Religion",
"The results of the Participation Survey broken down by Religion"},

"Participation Survey by Tenure" : { "Participation Survey by Tenure",
"The results of the Participation Survey broken down by Current Tenure"},

"Participation Survey by Urban-Rural classification" : { "Participation Survey by Urban-Rural Classification",
"The results of the Participation Survey broken down by Urban-Rural Classification"},

"Participation Survey by Use of data" : { "Participation Survey by Use of Data",
"The results of the Participation Survey by Comfort Engagement with Private and Public Data online."}}


# In[132]:


sepDf = df[ df['TabName'].str.contains('1b|1d|2b|2d|3b|3d|4b|5b|6b|7b|7c|7d|7e|8a|8d|8e|8f|8g|8h') ]

sepDf = sepDf.drop(columns=['TabName'])

sepFrames = {}

for i in sepDf['Question'].unique().tolist():

    if i in ["Aware of Her Majesty the Queen's Platinum Jubilee",
             "Aware of UNBOXED: Creativity in the UK",
             "Aware of Birmingham Commonwealth Games 2022",
             "Aware of Coventry City of Culture",
             "Engaged with the arts online in the last 12 months",
             "Engaged with the arts in person in the last 12 months",
             "Taken a holiday in England in the last 12 months",
             "Watched live sports in person in the last 6 months",
             "Used public library services digitally or online in the last 12 months",
             "Visited a museum or gallery in person at least once",
             "Visited a public library building or mobile library in person at least once",
             "Used heritage services digitally or online in the last 12 months",
             "Visited a heritage site in person at least once in the last 12 months",
             "How much you know about 5G mobile technology"]:

        continue
    
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

    #scraper.dataset.title = "Participation Survey by " + i.replace('/', '-')

    for x,y in metadata.items():
        if x.replace("Participation Survey by ", '') == i:
            scraper.dataset.title = sorted(list(y))[0]
            scraper.dataset.comment = sorted(list(y))[1]           

    frame.to_csv(pathify(i.replace('/', '-')) + '-observations.csv', index=False)

    catalog_metadata = scraper.as_csvqb_catalog_metadata()
    catalog_metadata.title = scraper.dataset.title
    catalog_metadata.summary = scraper.dataset.comment
    catalog_metadata.to_json_file(pathify(i.replace('/', '-')) + '-catalog-metadata.json')

    info.close()

    with open(pathify(i.replace('/', '-')) + "-info.json", "w") as outfile:
        json.dump(data, outfile, indent=4)


#sepDf.to_csv('Question-observations.csv', index=False)
#catalog_metadata = scraper.as_csvqb_catalog_metadata()
#catalog_metadata.to_json_file('Question-catalog-metadata.json')

frame


# In[133]:


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
        
        frame = frame.replace({'Response' : {'2021-06-03' : '3-6', '2021-10-07' : '7-10'}})

    for x,y in metadata.items():
        if x.replace("Participation Survey by ", '') == i:
            scraper.dataset.title = sorted(list(y))[0]
            scraper.dataset.comment = sorted(list(y))[1] 

    
    frame.to_csv(pathify(i.replace('/', '-')) + '-observations.csv', index=False)

    catalog_metadata = scraper.as_csvqb_catalog_metadata()
    catalog_metadata.title = scraper.dataset.title
    catalog_metadata.summary = scraper.dataset.comment
    catalog_metadata.to_json_file(pathify(i.replace('/', '-')) + '-catalog-metadata.json')

    info.close()

    with open(pathify(i.replace('/', '-')) + "-info.json", "w") as outfile:
        json.dump(data, outfile, indent=4)

#sepDf.to_csv('Survey-observations.csv', index=False)
#catalog_metadata = scraper.as_csvqb_catalog_metadata()
#catalog_metadata.to_json_file('Survey-catalog-metadata.json')

frame


# In[134]:


import os

useTheInternet = pd.read_csv("use-the-internet-observations.csv")

freqOfInternet = pd.read_csv("frequency-of-internet-use-observations.csv")

adultsUseOfInternet = pd.read_csv("adults-use-of-the-internet-smart-devices-observations.csv")

freqAndUse = freqOfInternet.append(useTheInternet)

freqAndUse = freqAndUse.rename(columns={'Survey Topic' : 'Question'})

freqAndUse['Question'] = freqAndUse.apply(lambda x: 'frequency-of-internet-use' if x['Question'] == 'adults-use-of-the-internet' else x, axis = 1)

adultsUseOfInternet = adultsUseOfInternet.append(freqAndUse)

os.remove("use-the-internet-observations.csv")
os.remove("frequency-of-internet-use-observations.csv")
os.remove("use-the-internet-info.json")
os.remove("frequency-of-internet-use-info.json")
os.remove("use-the-internet-catalog-metadata.json")
os.remove("frequency-of-internet-use-catalog-metadata.json")

adultsUseOfInternet.to_csv('adults-use-of-the-internet-smart-devices-observations.csv', index=False)

adultsUseOfInternet


# In[135]:


takenPartInTraining = pd.read_csv("taken-part-in-any-digital-or-online-skills-training-observations.csv")

adultsDigitalSkills = pd.read_csv("adults-digital-skills-observations.csv")

takenPartInTraining = takenPartInTraining.rename(columns={'Survey Topic' : 'Question'})

takenPartInTraining['Question'] = takenPartInTraining.apply(lambda x: 'taken-part-in-any-digital-or-online-skills-training' if x['Question'] == 'adults-digital-skills-demograhics' else x, axis = 1)

adultsDigitalSkills = adultsDigitalSkills.append(takenPartInTraining)

os.remove("taken-part-in-any-digital-or-online-skills-training-observations.csv")
os.remove("taken-part-in-any-digital-or-online-skills-training-info.json")
os.remove("taken-part-in-any-digital-or-online-skills-training-catalog-metadata.json")

adultsDigitalSkills.to_csv('adults-digital-skills-observations.csv', index=False)

adultsUseOfInternet


# In[136]:


"""1b 1d 2b 2d 3b 3d 4b 5b 6b 7b 7c 7d 7e 8a 8d 8e 8f 8g 8h"""


# In[ ]:




