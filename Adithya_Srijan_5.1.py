#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sun Mar  4 00:43:07 2018

@author: adithyajob ,Srijan 
"""

#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Mar  1 17:31:48 2018

@author: adithyajob
"""

import csv
from gurobipy import *
import geopy.distance
import gpxpy.geo
import sqlite3
from math import sin, cos, sqrt, atan2, radians

# approximate radius of earth in km
R = 6371.0

myData=[]
with open ('OR 604 Dominos Daily Demand.csv','r') as myFile:
    myReader=csv.reader(myFile)
    myReader.next()
    for row in myReader:
        myData.append((row[0].strip(),row[1].strip(),int(float( row[2].strip()))))
    #print len(myData)

# inputing the list into the database

#creatinon of the demand table
myConn=sqlite3.connect('Dominos_1.db')
myCursor=myConn.cursor()
SQLString="""CREATE TABLE IF NOT EXISTS tblDemand
(Demand_Date DATE, STORE_NUM STRING, Demand INTEGER);"""
myCursor.execute(SQLString)
myConn.commit()

#insert values into the table- 'demand'

SQLString="DELETE FROM tblDemand;"
myCursor.execute(SQLString)
myConn.commit()
SQLString="""INSERT INTO tblDemand VALUES(?,?,?);"""
myCursor.executemany(SQLString,myData)
myConn.commit()

#find store demand 
myData=[]
SQLString="""SELECT STORE_NUM, AVG(Demand)*4
FROM tblDemand
GROUP BY STORE_NUM;"""
myCursor.execute(SQLString)
myData=myCursor.execute(SQLString).fetchall() # store the values of avg daemaand in the dataframe myData
myConn.commit()
#create the tabel avgDemand
SQLString="""CREATE TABLE IF NOT EXISTS tblAvgDemand(STORE_NUM STRING, Avg_Demand DECIMAL);"""
myCursor.execute(SQLString)
myConn.commit()

# insert into the tabel avgDemand
SQLString="DELETE FROM tblAvgDemand;"
myCursor.execute(SQLString)
myConn.commit()
SQLString="""INSERT INTO tblAvgDemand VALUES(?,?);"""
myCursor.executemany(SQLString,myData)
myConn.commit()

#input the values of the stores data from the csv
myData=[]
with open ('OR604 Good Dominos Data.csv','r') as myFile:
    myReader=csv.reader(myFile)
    myReader.next()
    for row in myReader:
        myData.append((row[0].strip(),float(row[6].strip()),float( row[7].strip())))


#create the table to save the store data 
SQLString="""CREATE TABLE IF NOT EXISTS tblStore(STORE_NUM STRING, Lat DECIMAL, Long DECIMAL);"""
myCursor.execute(SQLString)
myConn.commit()

#INSERT THE STORE DATA INTO THE tblstore
SQLString="DELETE FROM tblStore;"
myCursor.execute(SQLString)
myConn.commit()
SQLString="""INSERT INTO tblStore VALUES(?,?,?);"""
myCursor.executemany(SQLString,myData)
myConn.commit()


## check the store which do not have a lat long 

SQLString="""DELETE  FROM tblAvgDemand WHERE  STORE_NUM  IN (SELECT DISTINCT a.STORE_NUM FROM tblAvgDemand AS a LEFT JOIN 
tblStore As b ON a.STORE_NUM=b.STORE_NUM WHERE b.STORE_NUM is Null);"""
myCursor.execute(SQLString)
myConn.commit() #### remove those store nums who donot have lat long 


### check the store nums who do not have any demand but have lat long 
myData=[]
SQLString="""SELECT DISTINCT a.STORE_NUM FROM tblStore AS a LEFT JOIN 
tblAvgDemand As b ON a.STORE_NUM=b.STORE_NUM WHERE b.STORE_NUM is Null;"""
myData=myCursor.execute(SQLString).fetchall()
myConn.commit()

#add this stores into avgdemand table
SQLString="""INSERT INTO tblAvgDemand VALUES(?,175*4);"""
myCursor.executemany(SQLString,myData)
myConn.commit()
#add dc data 
myData=[]
with open ('dc.csv','r') as myFile:
    myReader=csv.reader(myFile)
    for row in myReader:
        myData.append((row[0].strip(),float(row[1].strip()),float( row[2].strip()),float( row[3].strip()),float( row[4].strip())))

#create the supply tabel, comprsing of the supply side
SQLString="""CREATE TABLE IF NOT EXISTS tbldc(DC_NUM STRING, Lat DECIMAL, Long DECIMAL, Demand DECIMAL, Cost DECIMAL);"""
myCursor.execute(SQLString)
myConn.commit()

#INSERT THE DC DATA INTO THE tbldc
SQLString="DELETE FROM tbldc;"
myCursor.execute(SQLString)
myConn.commit()
SQLString="""INSERT INTO tbldc VALUES(?,?,?,?,?);"""
myCursor.executemany(SQLString,myData)
myConn.commit()

#######################Data_preparation_ends##############################################################



##### create lists for lat_longs of DC
myData = []
SQLString="""SELECT DC_NUM,Lat, Long  ,Cost, Demand FROM tblDC;"""
myCursor.execute(SQLString)
myData=myCursor.execute(SQLString).fetchall()
myConn.commit()
Dc_num = [x[0] for x in myData]
tuple(Dc_num)
Dc_lat= [x[1] for x in myData]
Dc_long= [x[2] for x in myData]
Cost_region = [x[3] for x in myData]
Supply= [x[4] for x in myData]
##### create lists for lat_longs of Stores 
myData = []
SQLString="""SELECT STORE_NUM, Lat, Long  FROM tblStore;"""
myCursor.execute(SQLString)
myData=myCursor.execute(SQLString).fetchall()
myConn.commit()
Store_num= [x[0] for x in myData]
tuple(Store_num)
Store_lat= [x[1] for x in myData]
Store_long= [x[2] for x in myData]


####create a miles dictionery 
miles={}
for store in Store_num :
    for dc in Dc_num:
        lat1 = radians(Store_lat[Store_num.index(store)])
        lon1 = radians(Store_long[Store_num.index(store)])
        lat2 = radians(Dc_lat[Dc_num.index(dc)])
        lon2 = radians(Dc_long[Dc_num.index(dc)])
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c* 0.621371
        miles[store,dc]=(distance)
        
temp=[]
mileslist=[]

for Store,dc in miles:
    temp=(Store,dc,miles[Store,dc])
    mileslist.append(temp)


SQLString="""CREATE TABLE IF NOT EXISTS tblmiles(STORE_NUM STRING, Dist_Num STRING, MILES DECIMAL);"""
myCursor.execute(SQLString)
myConn.commit()

SQLString="DELETE FROM tblmiles;"
myCursor.execute(SQLString)
myConn.commit()
SQLString="""INSERT INTO tblmiles VALUES(?,?,?);"""
myCursor.executemany(SQLString,mileslist)
myConn.commit()
    
      
##### create a cost dictionery 
Cost={}
for dc in Dc_num :
    Cost[dc]= Cost_region[Dc_num .index(dc)]

##### create a demand dictionery
myData = []
SQLString="""SELECT STORE_NUM, Avg_Demand FROM tblAvgDemand;"""
myCursor.execute(SQLString)
myData=myCursor.execute(SQLString).fetchall()   # fetched the demand from tblAvgDemand table
Demand_store_num= [x[0] for x in myData] #only used for this list as it is coming from a different csv
Demand= [x[1] for x in myData]
Demand_Store={}
for Store in Demand_store_num:
    Demand_Store[Store]= Demand[Demand_store_num.index(Store)]  

######create a Supply dictionery
# fetched the suppply from tbldc table
supply_dc={}
for dc in Dc_num:
    supply_dc[dc]= Supply[Dc_num.index(dc)]  
    
######MODELING STARTS###################################
#%% Create the model
domPizza = Model()
domPizza.ModelSense = GRB.MINIMIZE 
domPizza.setParam('MIPFocus',1)
domPizza.setParam('TimeLimit',600)
domPizza.setParam("MIPGap", 0.005)
domPizza.update()
domPizza.update()

#%% create the variables

# create a dictionary that will contain the gurobi variable objects
myVan = {}
for dc in Dc_num: 
    for store in Store_num:
        myVan[dc,store]= domPizza.addVar(obj = ((Cost[dc]*miles[store,dc]*Demand_Store[store])/9900.0), 
                                  vtype = GRB.BINARY, 
                                  name = 'x_%s_%s' % (store, dc)) # multiplying cost with miles 
domPizza.update()
        
    
#%% 
# create a dictionary that holds all constraints
myConstrs = {}
for store in Store_num:
    constrName = '%s_limits' % store
    myConstrs[constrName] = domPizza.addConstr(quicksum(myVan[dc,store]*int(round(Demand_Store[store])) for dc in Dc_num) 
                                           <= ((4.0*supply_dc[dc])/7), 
                                           name = constrName)
domPizza.update()
##%% create the supple constraint

#constrName = 'trs_limits'
#myConstrs[constrName] = domPizza.addConstr(quicksum(myVan[Van] for Van in myVan) 
                                           #==len(Store_num), 
                                           #name = constrName)

#domPizza.update()

for store in Store_num:
    constrName = 'trs_limits' 
    myConstrs[constrName] = domPizza.addConstr(quicksum(myVan[dc,store] for dc in Dc_num) 
                                           ==1 , 
                                           name = constrName)

domPizza.update()

#%% disply the model output
domPizza.write('mlip2.lp')
domPizza.optimize()


if domPizza.Status == GRB.OPTIMAL:
    print domPizza.ObjVal
    cost= domPizza.ObjVal
    obj_values= {'cost':cost}
          
if domPizza.Status == GRB.OPTIMAL:
    myConn = sqlite3.connect('Dominos_1.db')
    myCursor = myConn.cursor()
    domSolution = []
    domSolution_pizza_demand =[] 
    costSolution=[]
    for dc,store in myVan:
        if myVan[dc,store].x > 0:
            domSolution.append((dc,store, myVan[dc,store].x))
            domSolution_pizza_demand.append((dc,store, Demand_Store[store]))
    for cost in obj_values:
            costSolution.append((obj_values[cost]))

sqlString = """
            CREATE TABLE IF NOT EXISTS tbldom
            (  Distribution_Num STRING,Store_Number STRING,
            Decision INTEGER);
            """
            
myCursor.execute(sqlString)
myConn.commit()
sqlString = "DELETE FROM tbldom;"
myCursor.execute(sqlString)
sqlString = "INSERT INTO tbldom VALUES(?,?,?);"
myCursor.executemany(sqlString, domSolution)
myConn.commit()

sqlString = """
            CREATE TABLE IF NOT EXISTS tbldom_demand
            (  Distribution_Num STRING,Store_Number STRING,
            Demand Double);
            """
            
myCursor.execute(sqlString)
myConn.commit()
sqlString = "DELETE FROM tbldom_demand;"
myCursor.execute(sqlString)
sqlString = "INSERT INTO tbldom_demand VALUES(?,?,?);"
myCursor.executemany(sqlString, domSolution_pizza_demand)
myConn.commit()



sqlString_1 = """
            CREATE TABLE IF NOT EXISTS tbldomObj
           (Obj_Value DECIMAL);
              """
            
myCursor.execute(sqlString_1)
myConn.commit()

sqlString_1 = "DELETE FROM tbldomobj;"
myCursor.execute(sqlString_1)
sqlString_1 = "INSERT INTO tbldomobj VALUES(?);"
myCursor.execute(sqlString_1, costSolution)
myConn.commit()


myData_test = []
SQLString="""SELECT DISTINCT Store_Number FROM tbldom;"""
myCursor.execute(SQLString)
myData_test=myCursor.execute(SQLString).fetchall()


myCursor.close()
myConn.close()


