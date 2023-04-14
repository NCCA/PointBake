"""
  Copyright (C) 2011 Jon Macey

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import math
import sys
from typing import TextIO

import maya.cmds as cmds
import maya.OpenMaya as OM
import maya.OpenMayaAnim as OMA
import maya.OpenMayaMPx as OMX


def write_data(file : TextIO ,n_tabs : int ,data : str) -> None :
	""" write out to xml file with correct tabs
	Parameters :
		file (TextIO) the file pointer to write data too
		n_tabs (int) number of tabs to write before the data
		data (str) the actual data to write out to the file
	"""
	file.write("\t"*n_tabs)
	file.write(data)
	file.write("\n")

def NCCAPointBake(file_name : str,name : str ,start_frame : float ,end_frame : float) -> None :
	"""function to extract and write out the xml data to a file, we don't use any XML lib so there is no real check for correct formatting of the data, be carful!
	Parameters :
		file_name (str) the file name to open
		name (srt) name of the mesh selected
		start_frame (float)  the start frame for the export
		end_frame (float)  the end frame for the export
	"""
	# grab the selected object
	selected = OM.MSelectionList()
	obj=OM.MObject( )
	selected.add(name)
	selected.getDependNode(0,obj)
	# get the parent transform
	fn = OM.MFnTransform(obj)
	Mesh=""
	oChild = fn.child(0)
	# check to see if what we have is a mesh
	if(oChild.apiTypeStr()=="kMesh") :
		print ("got Mesh")
		# get our mesh
		Mesh=OM.MFnMesh(oChild)
	else :
		print (f"Didn't get mesh  {oChild.apiType()}")
		return

	with open(str(file_name[0]),'w') as file :
		current_frame=OM.MTime()
		anim=OMA.MAnimControl()
		# as these can take time to process we have an interupter to allow for the process to be
		# stopped
		interupter=OM.MComputation()
		# set the start of the heavy computation
		interupter.beginComputation()
		# now we set the tab level to 0 for the initial write to the file
		tab_indent=0

		# now we get the mesh number of points
		num_points = cmds.polyEvaluate( name, v=True)
		# write the xml headers
		file.write("<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n")
		file.write("<NCCAPointBake>\n")
		# up the tab level
		tab_indent=tab_indent+1
		# write the initial header data
		write_data(file,tab_indent,f"<MeshName> {name} </MeshName>")
		write_data(file,tab_indent,f"<NumVerts> {num_points} </NumVerts>")
		write_data(file,tab_indent,f"<StartFrame> {start_frame} </StartFrame>" )
		write_data(file,tab_indent,f"<EndFrame> {end_frame} </EndFrame>" )
		write_data(file,tab_indent,f"<NumFrames> {end_frame-start_frame} </NumFrames>" )
		write_data(file,tab_indent,f"<TranslateMode> absolute </TranslateMode>" )

		# now for every frame write out the vertex data
		for frame in range(start_frame,end_frame) :
			print (f"Doing frame {frame:04d}") 
			# move to the correct frame
			current_frame.setValue (frame)
			anim.setCurrentTime(current_frame)
			# write out the frame tag
			write_data(file,tab_indent,f'<Frame number="{frame}">' )
			tab_indent+=1
			for vertex in range(0,num_points) :
				# now the actual vertex data for the current mesh index value
				data = cmds.xform( (name+ ".vtx["+str(vertex)+"]"), q=True, ws=True, t=True )
				write_data(file,tab_indent,f'<Vertex number="{vertex}" attrib="translate"> {data[0]} {data[1]} {data[2]} </Vertex>')
			# now un-indent as we have ended the frame
			tab_indent-=1
			write_data(file,tab_indent,"</Frame>")
			# if we have interupted exit and finish
			if interupter.isInterruptRequested()  :
				file.write("</NCCAPointBake>\n")
				file.close()
				print ("File export interrupted ")
				return
		# now finish
		file.write("</NCCAPointBake>\n")
		# and close the file
		file.close()


class PointBakeExport() :
	"""export to a point bake xml file"""

	def __init__(self) :
		# get the currently selected objects and make sure we have only one object
		selected = OM.MSelectionList()
		OM.MGlobal.getActiveSelectionList(selected)
		self.selectedObjects = []
		selected.getSelectionStrings(self.selectedObjects)
		if len(self.selectedObjects) == 0 :
			cmds.confirmDialog( title='No objects Selected', message='Select a Mesh Object', button=['Ok'], defaultButton='Ok', cancelButton='Ok', dismissString='Ok' )
		elif len(self.selectedObjects) > 1 :
			cmds.confirmDialog( title='Select One Object', message='Only One Mesh may be exported at a time', button=['Ok'], defaultButton='Ok', cancelButton='Ok', dismissString='Ok' )
		# now we have the correct criteria we can proceed with the export
		else :
			# get the start and end values for our UI sliders
			anim=OMA.MAnimControl()
			minTime=anim.minTime()
			maxTime=anim.maxTime()
			self.start=int(minTime.value())
			self.end=int(maxTime.value())
			# now we create a window ready to populate the components
			self.window = cmds.window( title='NCCA Pointbake Export' )
			# create a layout
			cmds.columnLayout()
			# create two sliders for start and end we also attach methods to be called when the slider
			# changes
			self.startSlider=cmds.intSliderGrp( changeCommand=self.startChanged,field=True, label='Start Frame', minValue=self.start, maxValue=self.end, fieldMinValue=self.start, fieldMaxValue=self.end, value=self.start )
			self.endSlider=cmds.intSliderGrp( changeCommand=self.endChanged ,field=True, label='End Frame', minValue=self.start, maxValue=self.end, fieldMinValue=self.end, fieldMaxValue=self.end, value=self.end )
			# create a button and add the method called when pressed
			cmds.button( label='Export', command=self.export )
			# finally show the window
			cmds.showWindow( self.window )

	def export(self,*args) :
		# get the file name to save too
		basicFilter = "*.xml"
		file=cmds.fileDialog2(caption="Please select file to save",fileFilter=basicFilter, dialogStyle=2)
		# check we get a filename and then save
		if file !="" :
			if self.start >= self.end :
				cmds.confirmDialog( title='Range Error', message='start >= end', button=['Ok'], defaultButton='Ok', cancelButton='Ok', dismissString='Ok' )
			else :
				NCCAPointBake(file,self.selectedObjects[0],self.start,self.end)
				# finally remove the export window
				cmds.deleteUI( self.window, window=True )


	def startChanged(self, *args) :
		self.start=args[0]

	def endChanged(self, *args) :
		self.end=args[0]




















