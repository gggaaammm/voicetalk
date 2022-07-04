import spacy
import ast
import pandas as pd
import sqlite3
import time # time measure
import os
import sys
import glob # for reading multi files
import re # for number finding
#import the phrase matcher
from numerizer import numerize
from spacy.matcher import PhraseMatcher
from pint import UnitRegistry
#load a model and create nlp object
nlp = spacy.load("zh_core_web_sm")
#initilize the matcher with a shared vocab
matcher = PhraseMatcher(nlp.vocab)
# aside from english, chinese need some changes

# 1. a word segmentation before token classify(must)
from ckiptagger import data_utils, construct_dictionary, WS, POS, NER
start = time.time()
ws = WS("./data")   # word segmentation need 4 seconds
pos = POS("./data")
ner = NER("./data")

end = time.time()
print("loading time: ", end-start)
# 2. a special use of quantity managing(chosen)

#======= function readDB() ========
# in this function, program read files at the path "./dict/enUS/alias/"
# files data will be stored in dictionary: aliasDict
# aliasDict can be parsed by spaCy nlp()
# matcher() add the nlp() object, and give each key the match id
# no parameter, no return value is needed

def readDB():
    #create the list of alias to match
    path = r"dict/zhTW/alias/"                          #  path for alias
    all_files = glob.glob(os.path.join(path , "*.txt"))
    aliasDict={}                                        # create a dictionary of alias A/D/F/V/U

    # read all file at once
    for filename in all_files:
        sublist = []
        df = pd.read_csv(filename)
        for column in df.columns:
            sublist = sublist+list(df[column])             # read all elements in one file, stored as list
        sublist = [x for x in sublist if str(x) != 'nan']  # filter all NAN element in the list
        aliasDict[filename[21]] = sublist                  # key: filename[21] means A/D/F/V in "dict/enUS/alias/*.txt"


    #obtain doc object for each word in the list and store it in a list
    A = [nlp(a) for a in aliasDict['A']]
    D = [nlp(d) for d in aliasDict['D']]
    F = [nlp(f) for f in aliasDict['F']]
    V = [nlp(v) for v in aliasDict['V']]
    U = [nlp(u) for u in aliasDict['U']]


    #add the pattern to the matcher
    matcher.add("A", A)
    matcher.add("D", D)
    matcher.add("F", F)
    matcher.add("V", V)
    matcher.add("U", U)

    
    return aliasDict.values()

    
# ============  function textParse(sentence) ============
# main function of the spaCy, do the following:
# 1. read Database
# 2. match the token(tokenclassifier)
# 3. handle value
# 4. alias redirection
# 5. token counter validation(contain rule lookup)
# 6. token support check
# 7. token value check
# sentence(string) as input parameter, return value is device_queries
    

def textParse(sentence):
    # in chinese, do word segmentation before nlp
    
    
    alias_list_dict = readDB() # read database
    dict_for_CKIP = {}
    for alias_list in alias_list_dict:
        dict_for_CKIP.update( dict((el,1) for el in alias_list) )

    dict_for_CKIP = construct_dictionary(dict_for_CKIP)
    word_list = ws([sentence], coerce_dictionary=dict_for_CKIP) # wordlist for chinese number detection
    pos_list = pos(word_list)
    entity_list = ner(word_list, pos_list)
    print("[ckip pos]", pos_list)
    print("[ckip entity]", entity_list)
    
    
    sentence_space = ' '.join(word_list[0])
    print("[segmentation]", sentence_space)
    
    
    tokendict = {'A':'', 'D':'', 'F':'', 'V':'', 'U':''}  # new a dict: token dict, default key(A/D/F/V/U) is set with empty string
    
    # new a list: token
    token = ['','','','',''] #token[4] store rule/error bits, 
    
    device_queries = [[0]*5]*1 # init a device query(ies) which will send to devicetalk at the end of function
    
    
    # ====================   tokenclassifier start===================================
    # user matcher(doc) to classify words to tokens
    # unclassified word will be thrown away
    
    doc = nlp(sentence_space)  
    matches = matcher(doc)
    for match_id, start, end in matches:
        token_id = nlp.vocab.strings[match_id]  # get the token ID, i.e. 'A', 'D', 'F', 'V'
        span = doc[start:end]                   # get the object of word insentence
        print("token_id", token_id, "text", span.text)
    
        if(tokendict[token_id] == '' or tokendict[token_id] == span.text):   # if tokendict is  undefined or tokendict has same value
            tokendict[token_id] = span.text     # insert key and value in tokendict
        else:
            print("too much element in one token!") # error message #1: too much token
            token[4] = -1                           # store error bit in token[4](rule/error bit)
    # ====================   tokenclassifier end ===================================
    
    
    # ===========================  value handling start=================================
    # check if sentence contains number, before sentence redirecting
    # first remove other tokens(i.e, '1' in sentence: "set fan 1 speed to 3")

    sentence_space = sentence_space.replace(tokendict['D'], "")
    sentence_value = tokendict['V']
    
    
  # ========================== chinese number handling =========================
    
    
    word_list = ws([sentence_space], coerce_dictionary=dict_for_CKIP) # wordlist for chinese number detection
    pos_list = pos(word_list)
    entity_list = ner(word_list, pos_list)
    print("[ckip space]", pos_list)
    print("[ckip space]", entity_list)
    # in entity list , we only find out 1. cardianl 2. quanity 3. time
    entity_list = list(entity_list)
    print("[value list]", entity_list[0])
    for entity in entity_list[0]:
        print("[entity]", entity, type(entity))
        entity = list(entity)
        if(entity[2] == 'QUANTITY' or entity[2] == 'TIME' or entity[2] == 'CARDINAL' or entity[2] == 'ORDINAL' ):
            tokendict['V'] = handleValue(entity[3])
        else:
            print("not the thing i need to find")
        
    # last , we use handlevalue to calculate the value
    
    # =======================chinese number handling end ===============
    
    
    
    
    if(tokendict['V'] != ''):     # if token V has a string already matched, pass
        sentence_value = tokendict['V']  # save device name before alias redirect
        print("[numerizer] already have something in V")
        pass
    else:
        value_doc = nlp(sentence_space) # use spacy's extension: numerizer, converts numerical and quantitative words into numeric strings.
        print("value detect", value_doc._.numerize(), "in", sentence_space)
        df = pd.read_csv("dict/zhTW/num_zh.txt")
        if(len(value_doc._.numerize()) > 0): # if V is recognized as numeric strings, save it as a string of quantity 
            quantity = list(value_doc._.numerize().values())
            sentence_value = quantity
            print("[numerizer]quantity", quantity)
            #examine which chinese number need to be detected
            tokendict['V'] = handleValue(str(quantity[0])) # the string of quantity will be sent to handleValue()
        
    # ===========================  value handling end =================================
    
    


    sentence_feature = tokendict['F']     # save feature name before alias redirect
    sentence_device_name = tokendict['D'] if tokendict['D'] != '' else tokendict['A'] # save device name before alias redirect
    
    
    
    # ============================ alias redirection ================================
    # A,D,F,V alias should be redirect to device_model, device_name, device_feature individually
    path = r"dict/zhTW/alias/" #  path for synonym
    all_files = glob.glob(os.path.join(path , "*.txt"))
    for filename in all_files:
        sublist = []
        df = pd.read_csv(filename)
        #redirect A,D,F to device_model, device_name, device_feature individually
        #redirect V,U to default_value_name, unit_name
        for column in df.columns:
            df_abs = df.loc[(df[column] == tokendict[filename[21]])]
            if(len(df_abs.index)>0):
                tokendict[filename[21]] = df_abs.iloc[0][0]
                
    token = [tokendict['A'], tokendict['D'], tokendict['F'], tokendict['V'], token[4]]
    #============================ alias redirection end =================================

    # eliminate A if both AD exist
    if(token[0] != '' and token[1] != ''):
        token[0] = ''
        print('[elimination] list of token after A/D elimination:', token)

    # =========================== number of token validation  =======================================
    # check if number of tokens is enough.
    # if not enough, token[4] will record error id
    
    if(bool(token[0]!="") ^ bool(token[1]!="")): #check either A or D exist
        if(token[2]!=""):                        #check if F exist
            rule = ruleLookup(token[2])          # lookup rule by F
            token[4] = rule                      # token[4] record rule
            if(token[3]=="" and rule==2):        # check if V(for rule2) exist
                token[4]=-4                   # error message #4: device feature need value
        else:
            token[4]=-3                       # error message #3: no feature found in sentence 
    else:
        token[4]=-2                           # error message #2: no device found in sentence    
    
    # =========================== number of token validation end =======================================    
    
    
    
    #============================ support check =================================
    # if token has correct number, check if A/D support F
    if(token[4] > 0):                  # if error/rule bit records rules
        token[4] = supportCheck(token) # support check
    else:                              # if error/rule bit records errors
        print("[error]not enough token!") # break
    
    
    #============================ Value check =================================
    # if token has correct number and A/D support F, check if V is valid
    if(token[4] > 0): 
        device_queries = valueCheck(token, sentence_feature) # value check and get device queries
    else: # <0 because not support
        device_queries = token

    saveLog(sentence, token)   # save logs
    print("[final] before send to iottalk,", "\ndevice query", device_queries)
    return sentence_value, sentence_device_name, sentence_feature, device_queries
        

# ======= ruleLookup(feature) =======
# read the Table: DevicefeatureTable.txt
# look up the rule of the device feature and return rule number
# input parameter: feature(device_feature_name)
# return value: rule id, 1 for rule 1, 2 for rule 2, 0 for not found
    
def ruleLookup(feature): #check rule by feature
    # rulelookup will read DevicefeatureTable.txt
    print("token list check rule: ", feature)
    df = pd.read_csv('dict/DevicefeatureTable.txt')
    df = df.loc[(df['device_feature']==feature)]
    rule = df.iloc[0]['rule']
    if(rule == 1):
        return 1
    elif(rule == 2):
        return 2

# ======== supportCheck(tokenlist) =====
# read DeviceTable.txt, check if F exist in device_feature_list if 
# A/D match device_model/device_name
# if support, pass
# if not support, record the error bit(tokenlist[4])
# input parameter: tokenlist
# return value: tokenlist[4](error/value bit)

def supportCheck(tokenlist):
    A = tokenlist[0]
    D = tokenlist[1]
    F = tokenlist[2]
    # read device info in DeviceTable.txt
    df = pd.read_csv('dict/DeviceTable.txt')
    DeviceTable = readDeviceTable(A,D,F)
    
    if(D!=''):  #check if D supports F
        print("spotlight Device table check",DeviceTable )
        feature_list = ast.literal_eval(DeviceTable.iloc[0]['device_feature_list'])
        if(F not in feature_list):
            tokenlist[4] = -6   #error message#6: Device not support such feature
            
    if(A!=''): #check if A all support F
        allsupport,d_id = 1,0
        while (d_id < len(DeviceTable.index)):
            feature_list = ast.literal_eval(DeviceTable.iloc[d_id]['device_feature_list'])
            if(F not in feature_list):
                allsupport = 0
                break
            d_id = d_id+1

        if(allsupport == 0):
            tokenlist[4] = -6 #error message #6: Device not support such feature
            
    return tokenlist[4]


# ======== valueCheck(tokenlist, feature) ============

def valueCheck(tokenlist, feature): #issue give value
    A = tokenlist[0]
    D = tokenlist[1]
    F = tokenlist[2]
    V = tokenlist[3]
    rule = tokenlist[4]
    
    device_queries = [[0]*5]*1   # create a device query as return type of function

    
    df = pd.read_csv('dict/DevicefeatureTable.txt')

    if(rule == 1):      #(issue): Used for value_dict in devicefaturetable.txt
        print("rule 1") #give a value for rule 1 in value_keyword list
        df2 = pd.read_csv('dict/zhTW/alias/aliasF.txt')
        df2 = df2.loc[ (df2['alias1']==feature) | (df2['alias2']==feature) | (df2['alias3']==feature) |  (df2['alias3']==feature) | (df2['alias4']==feature)]
        feature = df2.iloc[0]['alias1']
        #feature change to absolute device feature('open'/'close')
        
        #require table of dictionary
        df = df.loc[(df['device_feature'] == F)]
        tokenlist[3] = ast.literal_eval(df.iloc[0]['value_dict'])[feature]
        
        if(D != ""):
            device_queries = [A,D,F,tokenlist[3], rule]
        if(A != ""):
            df_A = pd.read_csv('dict/DeviceTable.txt')   # read DeviceTable.txt
            df_A = df_A.loc[(df_A['device_model'] == A)] # access all the dataframe which device_model equals to A
            device_list =  list(df_A['device_name'])     # get the device name list which device_model is A
            device_queries = [[0]*5]*len(device_list)    # create a query for each device in 1 device model
            
            for idx, device in enumerate(device_list):
                device_queries[idx] = [A,device,F,tokenlist[3], rule]
        
        
    elif(rule ==2):
        # 1. a string(do nothing and pass)
        # 2. a number(check if exceed min/max)
        # 3. a quantity(check if unit support and check exceed min/max)
        
        if(D != ''):  #access the device info(which D and F are fitted)
            if(isinstance(V, int)):
                tokenlist[4] = checkMinMax(D,F,V)
                # a value, check number min/max
            elif(isinstance(V,str)):
                #find if string exist in value_dict, if yes, give value; if no, bypass string.
                df = findinfo(D,F)
                print("value check rule 2 df check", df)
                if(V in df.iloc[0]['value_dict']):
                    tokenlist[3] =  ast.literal_eval(df.iloc[0]['value_dict'])[V]
                    print("value check rule 2 string to int success: ", V)      
            else:
                print('a quantity')
                U = str(V).split(' ')[1] # check if unit in unit list
                if(len(df.loc[(df['device_name'] == D)&(df['unit_list'].str.contains(U))].index)>0):
                    print("value check rule 2 unit verified")
                    tokenlist[4] = checkMinMax(D,F,str(V).split(' ')[0])# already set to base unit, just extract the value 
                else:
                    tokenlist[4] = -8 # unsupport unit
                    print("value check rule 2 quantity unit error!")
            device_queries = tokenlist

                
                
            print("value check valid bit: ", tokenlist[4])
            
            
        elif(A != ''):
            print("A is ", A)
            df_A = pd.read_csv('dict/DeviceTable.txt')   # read DeviceTable.txt
            df_A = df_A.loc[(df_A['device_model'] == A)] # access all the dataframe which device_model equals to A
            device_list =  list(df_A['device_name'])     # get the device name list which device_model is A
            
            device_queries = [[0]*5]*len(device_list)    # create a query for each device in 1 device model
            
            
            #(issue) list 3 cases
            if(isinstance(V, int)):
                print('a number')
                # in while loop check min max
                
                for idx, device in enumerate(device_list):
                    device_queries[idx] = [A,device,F,V, checkMinMax(device, F, V)]
                print('device model value check number:', tokenlist)
                print('[device model] value check queries:', device_queries)

                # a value, check number min/max
            elif(isinstance(V,str)):
                print('a string')
                for idx, device in enumerate(device_list):
                    df = findinfo(device, F)
                    print('breakpoint #329:',type(V))
                    if(V in df.iloc[0]['value_dict']):
                        tokenlist[3] =  ast.literal_eval(df.iloc[0]['value_dict'])[V]
                    device_queries[idx] = [A,device,F,tokenlist[3],tokenlist[4]]
                        
                print('device model value check string:', tokenlist)
                print('[device model] value check queries:', device_queries)

                           
                #give a value to string or bypass string
            else:
                print('a quantity')
                for idx,device in enumerate(device_list):                    
                    U = str(V).split(' ')[1] # check if unit is in unit list
                    if(len(df.loc[(df['device_name'] == D)&(df['unit_list'].str.contains(U))].index)>0):
                        print("value check rule 2 unit verified")
                    else:
                        tokenlist[4] = -8 # unsupport unit
                        print("value check rule 2 quantity unit error!")
                        
                    V = str(V).split(' ')[0] # split a string into list, extract 1 element                
                    tokenlist[4] = checkMinMax(device,F,V)
                    device_queries[idx] = [A,device,F,V,tokenlist[4]]
                print('device model value check quantity:', tokenlist)
                print('[device model] value check queries:', device_queries)

    print("[valueCheck end] :", "device query:",device_queries, "\n tokenlist", tokenlist)    
    return device_queries


# ====== handleValue(quantity) ========
# check if quantity contains value and number
# if quantity contains only number, return number
# if quantity contains number and value, return the result of handleUnit(quantitylist)
# input parameter: quantity(a string contains numeric values)
# return value: quantitylist[0] or handleUnit(quantitylist)

def handleValue(quantity):
    print("[handleValue] quantity: ",quantity)
    quantitylist = quantity.split(' ') # split a string into list
    df = pd.read_csv("dict/zhTW/num_zh.txt")
    
    
    if(len(quantitylist) == 1):
        print("only value")
        value = quantitylist[0]
        #cannot find number, so we choose chinese
        if(value.isdigit() == False):
            print("it is a chinese number")
            df = df.loc[(df['text1'] == value) | (df['text2'] == value)]
            value = df.iloc[0]['value']
        print("value", value)
        return int(value)
    else:
        return handleUnit(quantitylist)

# ===== handleUnit(quantitylist) =======
# calculate the unit conversion of quantitylist
# read predefined base unit
# if number of quantitylist is even, calculate the result of unit conversion
# if number of quantitylist is 

def handleUnit(quantitylist): # use Pint package for unit hanlding 
    ureg = UnitRegistry()     # new a unit module
    Q_ = ureg.Quantity        # define a quantity element quantity = (value, unit)
    df = pd.read_csv(r"dict/zhTW/alias/aliasU.txt")
    df_n = pd.read_csv(r"dict/zhTW/num_zh.txt")
    #(issue)get base unit from iottalk define
    ureg.load_definitions('my_def.txt')
    ureg.default_system = 'iottalk'
    
    value = 0 #init value
    #(issue) When exception, catch the error message(wrong unit cannot be calculated. ex: 3 minute + 20 cm)
    if(len(quantitylist)%2 == 0):
        print("is by 2")
        for q_id in range(0, len(quantitylist),2):
            # redirection must be applied before unit calculation
            df_U = df.loc[(df['alias1'] == quantitylist[q_id+1]) | (df['alias2'] == quantitylist[q_id+1]) | (df['alias3'] == quantitylist[q_id+1])]
            quantitylist[q_id+1] = df_U.iloc[0]['U']
            df_N = df_n.loc[(df_n['text1'] == quantitylist[q_id]) | (df_n['text2'] == quantitylist[q_id])]
            quantitylist[q_id] = df_N.iloc[0]['value']
            value = value + Q_(int(quantitylist[q_id]), quantitylist[q_id+1]).to_base_units()
        print("[pint] base unit value:", value)
        return value
    else:
        print("error: is not by 2")
        return -5  # quantity error, number of value and unit mismatch
    
    
#followings are sub functions of value check
def checkMinMax(D,F, V): #check min max only for rule 2, 
    print(D,F,V)
    df = pd.read_csv('dict/DevicefeatureTable.txt')
    df_D= df.loc[(df['device_name'] == D) & (df['device_feature'] == F)]
    if( (float(V) > float(df_D.iloc[0]['max'])) | ( float(V) < float(df_D.iloc[0]['min'])) ): #if value exceed range
        return -7    # return -7 as error code
    else:
        return 2     # return 2 as rule 2

#
def findinfo(D,F):
    df = pd.read_csv('dict/DevicefeatureTable.txt')
    df = df.loc[(df['device_name'] == D) & (df['device_feature'] == F)]
    return df

def readDeviceTable(A,D,F):
    df = pd.read_csv('dict/DeviceTable.txt')
    if(D != ""):
        df = df.loc[df['device_name']== D]
    elif(A != ""):
        df = df.loc[df['device_model']== A]
    return df



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
    

