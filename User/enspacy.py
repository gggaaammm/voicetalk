import spacy
import DAN
import pandas as pd
import sqlite3
import re
#import the phrase matcher
from spacy.matcher import PhraseMatcher
#load a model and create nlp object
nlp = spacy.load("en_core_web_sm")
#initilize the matcher with a shared vocab
matcher = PhraseMatcher(nlp.vocab)
ServerURL = 'http://140.113.199.246:9999'      

def readDB():
    #create the list of words to match
    path_A_dict = r"dict/enUS/A_en.txt"
    A_dict = pd.read_csv(path_A_dict, sep="\n", header=None)
    A_dict.columns = ['A']
    A_list = list(A_dict['A'])

    path_D_dict = r"dict/enUS/D_en.txt"
    D_dict = pd.read_csv(path_D_dict, sep="\n", header=None)
    D_dict.columns = ['D']
    D_list = list(D_dict['D'])

    path_F_dict = r"dict/enUS/F_en.txt"
    F_dict = pd.read_csv(path_F_dict, sep="\n", header=None)
    F_dict.columns = ['F']
    F_list = list(F_dict['F'])

    path_V_dict = r"dict/enUS/V_en.txt"
    V_dict = pd.read_csv(path_V_dict, sep="\n", header=None)
    V_dict.columns = ['V']
    V_list = list(V_dict['V'])

    path_unit_dict = r"dict/enUS/unit_en.txt"
    unit_dict = pd.read_csv(path_unit_dict, sep="\n", header=None)
    unit_dict.columns = ['unit']
    unit_list = list(unit_dict['unit'])

    path_num_dict = r"dict/enUS/num_en.txt"
    num_dict = pd.read_csv(path_num_dict, usecols= ['text'])
    num_dict.columns = ['num']
    num_list = list(num_dict['num'])

    #obtain doc object for each word in the list and store it in a list
    A = [nlp(a) for a in A_list]
    D = [nlp(d) for d in D_list]
    F = [nlp(f) for f in F_list]
    V = [nlp(v) for v in V_list]
    unit = [nlp(unit) for unit in unit_list]
    num =  [nlp(num) for num in num_list]

    #add the pattern to the matcher
    matcher.add("A", A)
    matcher.add("D", D)
    matcher.add("F", F)
    matcher.add("V", V)
    matcher.add("unit", unit)
    matcher.add("num", num)
    #======

def exceptionHandle(word):
    print("need to be handled word",word)
    df = pd.read_csv(r"dict/num_en.txt")
    df = df.loc[df['text'] == word]
    value = df.iloc[0]['value']
    return value
    

    

def textParse(sentence):
    #process some text
    tokenlist = ['','','','','']
    unit = ''
    feature = ''
    doc = nlp(sentence)
    matches = matcher(doc)
    for match_id, start, end in matches:
        rule_id = nlp.vocab.strings[match_id]  # get the unicode ID, i.e. 'COLOR'
        span = doc[start:end]
        print(rule_id, span.text)
        # stored as sorted token list
        # if duplicate, mark tokenlist[4] as -1(invalid)
        if(rule_id == 'A'):
            tokenlist[0] = span.text
        elif(rule_id == 'D'):
            tokenlist[1] = span.text
        elif(rule_id == 'F'):
            tokenlist[2] = span.text
            feature = span.text
        elif(rule_id == 'V'):
            tokenlist[3] = span.text
        elif(rule_id == 'num'):
            value = exceptionHandle(span.text)
            print('text means value:', value)
            tokenlist[3] = int(value)
        elif(rule_id == 'unit'):
            unit = span.text

    # check the synonym, redirect to iottalk ver


    # eliminate A if both AD exist
    if(tokenlist[0] != '' and tokenlist[1] != ''):
        tokenlist[0] = ''
        print('tokenlist:', tokenlist)


    # check if sentence contains only one number
    pattern = '[0-9]+'
    numlist = re.findall(pattern, sentence)
    if(len(numlist) == 1):
        tokenlist[3] = numlist[0]

    # default : set 1st num as return value V
    
    token = tokenlist
    #1 check if enoght token A/D+F
    #when loop end, calculate token and check if valid.
    #sucess: token[4] = 1, E:token[4]=-1
    if(bool(token[0]!="") ^ bool(token[1]!="")):
        print("either A or D exist")
        #check if F exist
        if(token[2]!=""):
            print("F exist")
            rule = ruleLookup(token[2])
            token[4] = rule
            #check if V(for rule2) exist
            if(token[3]=="" and rule==2):
                print("need value")
                token[4]=-1
            elif(token[3]!="" and rule==2):
                print("V exist for rule 2")
        else:
            token[4]=-1
    else:
        token[4]=-1
        
    #now token has correct number, check if A/D support F
    if(token[4] != -1):
        token = supportCheck(token)
        print("do we need another synomon transform?", token)
    else:
        print("not enough token!")

    # check V has unit and need conversion
    if(unit != ''):
        token[3] = unitConversion(token[2], token[3], unit)
    else:
        print('no unit conversion required')


    # check for synonym and check the return value
    if(token[4] != -1 and rule==1):
        df = pd.read_csv('dict/enUS/supportlist_FVen.txt')
        df = df.loc[(df['F1']==tokenlist[2]) | (df['F2'] == tokenlist[2]) | (df['F3'] == tokenlist[2])]
        return_value = df.iloc[0]['R']
        tokenlist[3] = return_value
        # change F to iottalk device feature
        feature = tokenlist[2]
        tokenlist[2] = df.iloc[0]['Fiot']
        print("token list for return value(iottalk):", tokenlist)
    elif(token[4] != -1 and rule==2):
        df = pd.read_csv('dict/enUS/supportlist_FVen.txt')
        df = df.loc[(df['F1']==tokenlist[2]) | (df['F2'] == tokenlist[2]) | (df['F3'] == tokenlist[2])]
        # change F to iottalk device feature
        tokenlist[2] = df.iloc[0]['Fiot']

    print("last before send to iottalk", tokenlist)
    sendIot(tokenlist)
    saveLog(sentence, tokenlist)
    print("voice input feature: ", feature)
    return feature, tokenlist
        

    
def ruleLookup(feature):
    print("token list check rule")
    df = pd.read_csv('dict/enUS/rule_en.txt')
    df = df.loc[df['feature']==feature]
    rule = df.iloc[0]['rule']
    if(rule == 1):
        return 1
    else:
        return 2
    return 0
    
def supportCheck(tokenlist):
    print("tokenlist before support check: ", tokenlist)
    # unified synonym
    df = pd.read_csv('dict/synonym.txt')
    df = df.loc[(df['F1']==tokenlist[2]) | (df['F2'] == tokenlist[2]) | (df['F3'] == tokenlist[2])]
    print("df exist:", df)
    print(df.iloc[0]['F'])
    feature = df.iloc[0]['F']
    print("my feature only name", feature)
    
    # read support list to check if D support F
    #check if D supports F
    if(tokenlist[1]!=''):
        df = pd.read_csv('dict/enUS/supportlist_ADFen.txt')
        print("why no D", tokenlist[1])
        print("D list:\n", df['D'])
        df = df.loc[df['D']==tokenlist[1]]
        print("= = why not parse", df, tokenlist[1])
        if(df.iloc[0]['F1']==feature or df.iloc[0]['F2']==feature):
            print('D support F')
        else:
            print('D not support F')
            tokenlist[4] = -1
    
    #check if A support F
    if(tokenlist[0]!=''):
        allsupport = 1
        df = pd.read_csv('dict/enUS/supportlist_ADFen.txt')
        df = df.loc[df['A']==tokenlist[0]]
        print("all belongs to A:", df)
        d_id = 0
        while (d_id < len(df.index)):
            if(df.iloc[d_id]['F1']!= feature and df.iloc[d_id]['F2']!=feature):
                print('one of D unsupport')
                allsupport = 0
                break
            d_id = d_id+1
    
        if(allsupport == 1):
            print('A all support F')
        else: tokenlist[4] = -1
            
    return tokenlist

def sendIot(tokenlist):
    if(tokenlist[1]!="" and tokenlist[4]!=-1): # D+F
        df = pd.read_csv('dict/ADF.txt')
        print('df info:', df, "searching", tokenlist[1])
        df = df.loc[df['D_ens']==tokenlist[1]]
        print("remain df", df)
        deviceName = df.iloc[0]['D_en']
        deviceModel = df.iloc[0]['A_en']
        dfList = df.iloc[0]['DFlist']
        Regaddr = df.iloc[0]['Regaddr']
        dfList = eval(dfList)
        print(type(dfList))
        returnValue = tokenlist[3]
        deviceFeature = tokenlist[2]
        print("device name: ",deviceName,"device model: ", deviceModel)
        Reg_addr = Regaddr
        DAN.profile['d_name']= deviceName # search for device name 
        DAN.profile['dm_name']=deviceModel # use specific device model 
        DAN.profile['df_list']=dfList
        DAN.device_registration_with_retry(ServerURL, Reg_addr)
        DAN.push(deviceFeature, int(returnValue))
    
    if(tokenlist[0]!="" and tokenlist[4]!=-1): #  A+F
        df = pd.read_csv('dict/ADF.txt')
        df = df.loc[df['A_ens']==tokenlist[0]]
        print('df info:',df)
        for ind in df.index:
            print(df['D_en'][ind], df['A_en'][ind], df['DFlist'][ind], df['Regaddr'][ind])
            deviceName = df['D_en'][ind]
            deviceModel = df['A_en'][ind]
            dfList = df['DFlist'][ind]
            Regaddr = df['Regaddr'][ind]
            dfList = eval(dfList)
            returnValue = tokenlist[3]
            deviceFeature = tokenlist[2]
            print("device name: ",deviceName,"device model: ", deviceModel )
            Reg_addr = Regaddr
            DAN.profile['d_name']= deviceName # search for device name 
            DAN.profile['dm_name']=deviceModel # use specific device model 
            DAN.profile['df_list']=dfList
            DAN.device_registration_with_retry(ServerURL, Reg_addr)
            DAN.push(deviceFeature, int(returnValue))

    print("send to iottalk", tokenlist)



def saveLog(sentence, tokenlist):
    print('save log')
    connection = sqlite3.connect("db/log.db")
    crsr = connection.cursor()
    # SQL command to insert the data in the table
    sql_command = """CREATE TABLE IF NOT EXISTS log ( 
    sentence TEXT,  
    result CHAR(1)
    );"""
    crsr.execute(sql_command)

    
    crsr.execute(f'INSERT INTO log VALUES ( "{sentence}", "{tokenlist[4]}")')

    connection.commit()
    connection.close()
    

def unitConversion(feature, numeral, unit):
    print('unit conversion', feature, 'for', numeral, 'and', unit)
    df = pd.read_csv('dict/enUS/quantityen.txt')
    df = df.loc[df['F_en'] == feature]

    if(feature == 'rotation'):
        if(unit == 'percent'):
            return int(numeral)*3.6
        else:
            return int(numeral)

