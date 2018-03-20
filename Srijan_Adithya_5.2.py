#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 15 04:44:02 2018

@author: adithyajob ,Srjan

"""

import csv
from gurobipy import *
import sqlite3
import geopy.distance
import gpxpy.geo
from math import sin, cos, sqrt, atan2, radians
R = 6371.0
#%% Create daily demand file
myConn=sqlite3.connect('Dominos_1.db')
myCursor=myConn.cursor()
SQLString="""DROP TABLE IF EXISTS tblDemand_Flour"""
myCursor.execute(SQLString)
myConn.commit()
SQLString="""CREATE TABLE tblDemand_Flour AS 
SELECT Distribution_Num,SUM(Demand)  AS DC_DEMAND,ROUND(sum(Demand)*(0.28*3) ,2) AS FlourDlb,
(case when ROUND((sum(Demand)*(0.28*3))/50 , 2) = cast(ROUND((sum(Demand)*(0.28*3))/50 , 2) as int) then cast(ROUND((sum(Demand)*(0.28*3))/50 , 2) as int)
                else 1 + cast(ROUND((sum(Demand)*(0.28*3))/50 , 2) as int) end) unit_demand
FROM tbldom_Demand
GROUP BY Distribution_Num;"""
myCursor.execute(SQLString)
myConn.commit()

myData=[]
with open ('Supplier_Data.csv','r') as myFile:
    myReader=csv.reader(myFile)
    myReader.next()
    for row in myReader:
        myData.append((row[0].strip(),float(row[1].strip()),float( row[2].strip()),int( row[3].strip()),float( row[4].strip()),float( row[5].strip()),int( row[6].strip())))
        
SQLString="""CREATE TABLE IF NOT EXISTS tblSupplier_Data(Mill STRING,
Lat FLOAT,Long FLOAT,Capacity INTEGER,Costpunit FLOAT,
Costpmile FLOAT,Fixed_cost INTEGER);"""

myCursor.execute(SQLString)  
myConn.commit()
SQLString="DELETE FROM tblSupplier_Data;"""
myCursor.execute(SQLString)
myConn.commit()
SQLString="INSERT INTO tblSupplier_Data VALUES(?,?,?,?,?,?,?);"""
myCursor.executemany(SQLString,myData)
myConn.commit()

myData=[]
SQLString="""SELECT a.DC_NUM,a.lat,a.long,b.mill,b.lat,b.long
                FROM tbldc a, tblSupplier_Data b;"""
rowData=myCursor.execute(SQLString).fetchall()

lat_dc = [x[1] for x in rowData]
long_dc= [x[2] for x in rowData]
lat_mill= [x[4] for x in rowData]
long_mill= [x[5] for x in rowData]
Mill_num= [x[3] for x in rowData]
Dc_num = [x[0] for x in rowData]
miles_={}
for mill in Mill_num:
    for dc in Dc_num:
        lat1 = radians(lat_mill[Mill_num.index(mill)])
        lon1 = radians(long_mill[Mill_num.index(mill)])
        lat2 = radians(lat_dc[Dc_num.index(dc)])
        lon2 = radians(long_dc[Dc_num.index(dc)])
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c* 0.621371
        miles_[mill,dc]=(distance)
temp=[]
mileslist=[]

for mill,dc in miles_:
    temp=(mill,dc,miles_[mill,dc])
    mileslist.append(temp)   
    
SQLString="""DROP TABLE IF EXISTS tblmiles;"""
myCursor.execute(SQLString)
myConn.commit()

SQLString="""CREATE TABLE IF NOT EXISTS tblSup_Dc_miles(mill STRING, DC_NUM STRING, miles DECIMAL);"""
myCursor.execute(SQLString)
myConn.commit()
SQLString="""INSERT INTO tblSup_Dc_miles VALUES(?,?,?);"""
myCursor.executemany(SQLString,mileslist)
myConn.commit()

miles={}
dc_num=[]
mills=[]
demand={}
fxcost={}
costpunit={}
costpmle={}
supply={}

SQLString="""SELECT mill,capacity,costpunit,costpmile,fixed_cost FROM tblSupplier_Data;"""
mydata=myConn.execute(SQLString)
myConn.commit()
for row in mydata:
    mills.append(row[0])
    supply[row[0]]=row[1]
    costpunit[row[0]]=row[2]  
    costpmle[row[0]]=row[3]
    fxcost[row[0]]=row[4]

SQLString="""select mill,DC_NUM,miles from tblSup_Dc_miles;"""
mydata=myConn.execute(SQLString)
myConn.commit()
for row in mydata:
    miles[row[0],row[1]]=row[2]
#print miles
SQLString="""SELECT Distribution_Num,unit_demand FROM tblDemand_Flour;"""
mydata=myConn.execute(SQLString)
myConn.commit()
for row in mydata:
     dc_num.append(row[0])
     demand[row[0]]=row[1]
#%% Create the model
flrModel = Model()
flrModel.setParam('MIPFocus',1)
flrModel.setParam('TimeLimit',400)
flrModel.setParam("MIPGap", 0.005)
flrModel.modelSense = GRB.MINIMIZE
flrModel.update()
#%% create the variables

# create a dictionary that will contain the gurobi variable objects
myedge = {}
for mill in mills: 
    for dc in dc_num:
        myedge[mill,dc]= flrModel.addVar(obj = (demand[dc]*costpunit[mill]+(demand[dc]*miles[mill,dc]*costpmle[mill])/880.0), 
                                  vtype = GRB.BINARY, 
                                  name = 'x_%s_%s' % (mill, dc))  
flrModel.update()
mytool={}
for mill in mills: 
        mytool[mill]= flrModel.addVar(obj = fxcost[mill], 
                                  vtype = GRB.BINARY, 
                                  name = 'tool_%s' % mill)   
flrModel.update()

#%%
# create a dictionary that holds all constraints
myConstrs = {}

##%% create the supply constraint

for mill in mills:
    constrName = 'Mill%s_limits' % dc
    myConstrs[constrName] = flrModel.addConstr(quicksum(myedge[mill,dc]*demand[dc] for dc in dc_num) 
                                           <= (4/7.0)*(supply[mill]*mytool[mill]), 
                                           name = constrName)
flrModel.update()
for dc in dc_num:
    constrName = 'DC%s_limits' % dc
    myConstrs[constrName] = flrModel.addConstr(quicksum(myedge[mill,dc] for mill in mills) 
                                           ==1, 
                                           name = constrName)
flrModel.update()
#%% 
flrModel.write('mlip.lp')
flrModel.optimize() 
#%% save results in a database
if flrModel.Status == GRB.OPTIMAL:
    print flrModel.ObjVal
    cost= flrModel.ObjVal
    obj_values= {'cost':cost}
    
    
if flrModel.Status == GRB.OPTIMAL:
    myConn = sqlite3.connect('Dominos_1.db')
    myCursor = myConn.cursor()
    flourSol = []
    for edge in myedge:
        if myedge[edge].x > 0:
              flourSol.append((edge[0],edge[1], myedge[edge].x))
    toolSol=[]    
    for tool in mytool:
        if mytool[tool].x > 0:
              toolSol.append((tool, mytool[tool].x))
    costSolution=[]
    for cost in obj_values:
            costSolution.append((obj_values[cost]))
            
SQLString="""DROP TABLE IF EXISTS tblFlour;"""
myCursor.execute(SQLString)
myConn.commit()
sqlString = """
                CREATE TABLE tblFlour
                (mill      TEXT,
                 DC_NUM    TEXT,
                 Decision   DOUBLE);
                """
myCursor.execute(sqlString)
myConn.commit()
    
# create the insert string
sqlString = "INSERT INTO tblFlour VALUES(?,?,?);"
myCursor.executemany(sqlString, flourSol)    
myConn.commit()
SQLString="""DROP TABLE IF EXISTS tool;"""
myCursor.execute(SQLString)
myConn.commit()
sqlString = """
                CREATE TABLE tool
                (mill      TEXT,
                 open      DOUBLE);
                """
myCursor.execute(sqlString)
myConn.commit()
sqlString = "INSERT INTO tool VALUES(?,?);"
myCursor.executemany(sqlString, toolSol)    
myConn.commit()
    
sqlString_1 = """
            CREATE TABLE IF NOT EXISTS tblflrObj
           (Flr_Obj_Value DECIMAL);
              """
            
myCursor.execute(sqlString_1)
myConn.commit()

sqlString_1 = "DELETE FROM tblflrObj;"
myCursor.execute(sqlString_1)
sqlString_1 = "INSERT INTO tblflrobj VALUES(?);"
myCursor.execute(sqlString_1, costSolution)
myConn.commit()

myCursor.close()
myConn.close()      
