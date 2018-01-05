import arcpy,time
from arcpy.sa import *
from arcpy import env
import numpy as np
arcpy.CheckOutExtension("spatial")
arcpy.env.overwriteOutput = True






demRaster = arcpy.GetParameterAsText(0)
workspace = arcpy.GetParameterAsText(1)
set_threshold_manually = arcpy.GetParameterAsText(2)
env.workspace = workspace


filled =workspace + "\\" + "filled"
flow_dir = workspace + "\\" + "flow_dir"
flow_acc = workspace + "\\" + "flow_acc"
watershed = workspace + "\\" + "watershed"
result = workspace + "\\HAND"

drainage_net = workspace + "\\" + "drainage_net"
actual_drainage_network = workspace +"\\actual_dr"

riverf_shp = workspace + "\\" + "drainage_pt.shp"
riverfelevated_shp = workspace + "\\" + "drain_pt_val.shp"

start_of_drainages= "p_o_start"
start_of_drainages2= "p_o_start2"
start_of_drainages_fullpath= workspace + "\\" + start_of_drainages +".shp"
start_of_drainages2_fullpath= workspace + "\\" + start_of_drainages2 +".shp"

########################################
arcpy.SetProgressor("step", "propering layers...", 0, 6, 1)
arcpy.SetProgressorLabel("message")
arcpy.SetProgressorPosition(1)
#############################################

arcpy.AddMessage("filling dem raster")
outFill = Fill(demRaster)
outFill.save(filled)

def sorter(myset):
	myset2 = {}
	for x in myset:
		myset2[x] = x
	import operator
	sorted_x = sorted(myset2.items(), key=operator.itemgetter(1))
	sorted2 =[]
	for cc in sorted_x: sorted2.append(cc[1])
	return sorted2


def median_(your_raster):
	mynumpy= arcpy.RasterToNumPyArray(your_raster,"","","",-9999)
	a_ = np.ma.masked_array(mynumpy, mynumpy == -9999)
	a_ = a_.compressed()

	sorted = list(a_)
	temp = []
	for x in sorted: temp.append(x)
	#arcpy.AddMessage(type(temp))
	sorted = temp.sort()

	length= int(len(temp) / 2)
	median_ = temp[length]
	return temp,median_

def count_cells(your_raster):
	mynumpy= arcpy.RasterToNumPyArray(your_raster,"","","",-9999)
	mynumpy_no_nodata = np.ma.masked_array(mynumpy, mynumpy == -9999)
	how_many = len(np.where(mynumpy>-9999)[0])
	return how_many,np.min(mynumpy_no_nodata),np.max(mynumpy_no_nodata),np.mean(mynumpy_no_nodata)



def get_unique_point(line_layer,start_of_drainages="p_o_start"):
	global start_of_drainages_fullpath
	arcpy.CreateFeatureclass_management(workspace ,start_of_drainages,"Multipoint","","DISABLED","DISABLED",line_layer)
	geometries = arcpy.CopyFeatures_management(line_layer,arcpy.Geometry())
	#arcpy.AddMessage("-"*22)
	startlist =[]
	lastlist =[]
	for geometry in geometries:
		startlist.append([round(geometry.firstPoint.X, 2),round(geometry.firstPoint.Y, 2)])
		lastlist.append([round(geometry.lastPoint.X, 2),round(geometry.lastPoint.Y, 2)])

	unique_list=[]
	for x in startlist:
		if x not in lastlist:
			unique_list.append(x)

	for zz in unique_list:
		array = arcpy.Array(arcpy.Point(zz[0], zz[1]))
		Multipoint = arcpy.Multipoint(array)
		cursor = arcpy.da.InsertCursor(start_of_drainages_fullpath,"SHAPE@")
		cursor.insertRow((Multipoint,))
		del cursor
	#arcpy.AddMessage(startlist)
		




########################################
#arcpy.SetProgressor("step", "propering layers...", 0, 6, 2)
arcpy.SetProgressorLabel("message")
arcpy.SetProgressorPosition(2)
#############################################

arcpy.AddMessage("create Flow Direction layer")
FlowDirection = FlowDirection(filled, "")
FlowDirection.save(flow_dir)

########################################
#arcpy.SetProgressor("step", "propering layers...", 0, 6, 3)
arcpy.SetProgressorLabel("message")
arcpy.SetProgressorPosition(3)
#############################################
arcpy.AddMessage("create Flow Accumulation layer")
FlowAccumulation = FlowAccumulation(flow_dir, "", "FLOAT")
FlowAccumulation.save(flow_acc)



def table_to_list(shp,col):
	suma =[]
	curs = arcpy.da.SearchCursor(shp,col)
	for row in curs:
		suma.append(row[0])
	return suma






expr_result = 0
def find_exp(flow_acc,expr,cellcount_of_river,acc_list):

   global expr_result 
   if len(acc_list) > 1:
	Expressionf = "value > " + str(expr)	#min
	#arcpy.AddMessage("_____")
	#arcpy.AddMessage("my lenth is:" + str(len(acc_list)))
	#arcpy.AddMessage(str(expr))
	outCon = Con(flow_acc, "1", "", Expressionf)
	cellcount_of_out = count_cells(outCon)[0]
	#arcpy.AddMessage(type(cellcount_of_river))
	if cellcount_of_river < cellcount_of_out:
			#arcpy.AddMessage("river < cellcount")

			length= int(len(acc_list) / 2)
			median_1 = acc_list[length]

			#arcpy.AddMessage(int(median_1))
			acc_list = acc_list[length:]	#int(median_1):]
			find_exp(flow_acc,median_1,cellcount_of_river,acc_list)
	else:

			length= int(len(acc_list) / 2)
			median_1 = acc_list[length]

			#arcpy.AddMessage(int(median_1))
			#arcpy.AddMessage(acc_list)
			acc_list = acc_list[:length]	#acc_list[:int(median_1)]
			find_exp(flow_acc,median_1,cellcount_of_river,acc_list)
   else:
	expr_result = int(expr) #int(expr.tolist())
	return 1 #int(expr.tolist())

def get_threshold_automatically(true_river):
	global demRaster,workspace,flow_acc,acc_start_of_river,start_of_drainages, start_of_drainages2,actual_drainage_network,start_of_drainages_fullpath,start_of_drainages2_fullpath

	get_unique_point(true_river,start_of_drainages="p_o_start")
	arcpy.FeatureToPoint_management(start_of_drainages_fullpath, start_of_drainages2_fullpath, "CENTROID")
	acc_value_of_ob_river = ExtractMultiValuesToPoints(start_of_drainages2_fullpath, [[flow_acc, "acc"]], "NONE")
	acc_start_of_river = table_to_list(start_of_drainages2_fullpath, "acc")

	elevSTDResult = arcpy.GetRasterProperties_management(demRaster, "CELLSIZEX")
	elev_cell_size = int(elevSTDResult.getOutput(0))
	#arcpy.AddMessage(true_river)
	#arcpy.AddMessage(str(elev_cell_size))
	oid = arcpy.Describe(true_river).OIDFieldname	#"FID"
	arcpy.PolylineToRaster_conversion(true_river, oid, actual_drainage_network,"MAXIMUM_LENGTH", "NONE", elev_cell_size)
	cellcount_of_river =count_cells(actual_drainage_network)[0]
	acc_list=median_(flow_acc)[0]
	#myset = list(set(acc_list))

	myset = list(set(acc_start_of_river))
	sorted2 = sorter(myset)
	#arcpy.AddMessage(sorted2)
	my_exp = find_exp(flow_acc,sorted2[0],cellcount_of_river,sorted2)
	#arcpy.AddMessage(expr_result )

if set_threshold_manually == "Manual":
	########################################
	#arcpy.SetProgressor("step", "propering layers...", 0, 6, 4)
	arcpy.SetProgressorLabel("message")
	arcpy.SetProgressorPosition(4)
	#############################################

	expr_result = int(arcpy.GetParameterAsText(3))
else:
	########################################
	#arcpy.SetProgressor("step", "propering layers...", 0, 6, 4)
	arcpy.SetProgressorLabel("message")
	arcpy.SetProgressorPosition(4)
	#############################################

	arcpy.AddMessage("calculating threshold")
	get_threshold_automatically(arcpy.GetParameterAsText(4))
	arcpy.AddMessage("threshold has been calculated: " + str(expr_result))


Expressionf = "value > " + str(expr_result)
outCon = Con(flow_acc, "1", "", Expressionf)
outCon.save(drainage_net)






####### hand
########################################
#arcpy.SetProgressor("step", "propering layers...", 0, 6, 5)
arcpy.SetProgressorLabel("message")
arcpy.SetProgressorPosition(5)
#############################################

arcpy.RasterToPoint_conversion(drainage_net, riverf_shp, "VALUE")
outWatershed = ExtractValuesToPoints(riverf_shp, demRaster, riverfelevated_shp, "NONE", "VALUE_ONLY")
arcpy.env.extent = "MAXOF"
outWatershed = Watershed(flow_dir, riverfelevated_shp, "RASTERVALU")
outWatershed.save(watershed)

outMinus = Minus(demRaster, watershed)

#outMinus.save(result + "_neg_" + str(int(expr_result)))
outCon = Con(outMinus, 0, outMinus, "value <= 0")
outCon.save(result + "_" + str(int(expr_result)))


mxd = arcpy.mapping.MapDocument("CURRENT")
dataFrame = arcpy.mapping.ListDataFrames(mxd, "*")[0] 
addLayer = arcpy.mapping.Layer(result + "_" + str(int(expr_result)))
arcpy.mapping.AddLayer(dataFrame, addLayer)

########################################
#arcpy.SetProgressor("step", "propering layers...", 0, 6, 6)
arcpy.SetProgressorLabel("message")
arcpy.SetProgressorPosition(6)
#############################################
