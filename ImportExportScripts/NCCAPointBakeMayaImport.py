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
import xml.sax

import maya.cmds as cmds
import maya.OpenMaya as OM
import maya.OpenMayaAnim as OMA
import maya.OpenMayaMPx as OMX

"""@package docstring
This module will allow the selection of an obj file and a xml based NCCA Point bake file and
load in point baked animation to a maya scene. The user is prompted for a base node name
which is pre-pended to all elements create in the loading process,

@author Jonathan Macey
@version 1.0
@date Last Revision 10/01/11 fixed bug in xml parse
 previous updates :
 Updated to NCCA Coding standard

"""



class ParseHandler(xml.sax.ContentHandler):
	"""wrap the processing of the xml.sax parser, all of the methods are called
	from this class however the class data is specific to the parsing process. In this case it is a
	parser for the NCCA PointBake file format
	"""
	def __init__(self,selected_text : str )-> None :
		"""constructor for parser passes in the correct text to be processed
		Parameters :
			 selected_text (str) the mesh the data is to be loaded too
		"""
		##  the object selected to load the data too.
		self.selected_object=selected_text
		##  the Character Data stored as part of parsing
		self.char_data=""
		##  the meshname extracted from the PointBake file
		self.meshname=""
		##  number of vertices in the mesh, we will check this against the number of points in
		## the mesh / obj loaded as a basic compatibility check
		self.num_verts=0
		##  the Start frame for the data loaded
		self.start_frame=0
		##  end_frame of the data loaded
		self.end_frame=0
		##  number of frames stored in file not used in this example
		self.num_frames=0
		##  the Offset into the vertex list for the current data to be set too
		self.offset=None
		##  the Current frame to be stored / keyed
		self.current_frame=0
		# the maya time control
		self.m_anim=OMA.MAnimControl()
		# a point array structure, we will load each frame's worth of data into this then
		# load it to the mesh point data each frame, once this is done we need to clear this data for
		# the next frame
		self.vert_data=OM.MFloatPointArray()
		# grab the object ready to set the point data
		selected = OM.MSelectionList()
		obj=OM.MObject()
		print(f"Debug {self.selected_object=}")
		print(f"Debug {type(self.selected_object)}")
		selected.add(self.selected_object)
		selected.getDependNode(0,obj)

		fn = OM.MFnTransform(obj)
		self.mesh=""
		oChild = fn.child(0)

		if(oChild.apiTypeStr()=="kMesh") :
			print ("got Mesh")
			# get our mesh
			self.mesh=OM.MFnMesh(oChild)
		# set the frame to start


	def __del__(self) :
		print ("done")
	##  here we trigger events for the start elements In this case we grab the Offset and Frame
	## @param[in] name the name of the tag to process
	## @param[in] attrs the attribute associated with the current tag
	def startElement(self, name, attrs):
		# this is important the characters method may be called many times so we
		# clear the char data each start element then append each time we read it
		self.char_data=""
		# if we have a vertex start tag process and extract the offset
		if name == "Vertex" :
			self.offset=int(attrs.get("number"))
		# if we have the Frame we grab the number attribute
		elif name == "Frame" :
			# set the frame here
			self.current_frame=int(attrs.get("number"))
			self.m_anim.setCurrentTime(OM.MTime(self.current_frame))
			# we have a new frame so re-set the vertexPoint data ready to be filled
			# with the new dara
			self.vert_data.clear()

	##  trigger method if we have data between the <> </> tags, copy it to the class char_data so
	## we can re-use it later
	## @param[in] _content the character string passed from the parser.
	def characters(self,content):
		# here we append the content data passed into the method, we need to append
		# as this function may be called more than once if we have a long string
		self.char_data += content

	##  most of the hard processing is done here. Once an end tag is encountered we
	## process the current char data and add it to the channel created. This does
	## rely on the order of the data but this is always machine generated so we should
	## be safe if it does go wrong it will be this data ordering
	## [in] name the name of the end element tag
	def endElement(self, name):
		# extract the meshname and save it
		if name == "MeshName":
			self.meshname=self.char_data
		# get the number of vertices and set this to the channel
		elif name == "NumVerts" :
			# store value
			self.num_verts=int(self.char_data)

		# parse and sel the start_frame
		elif name == "StartFrame" :
			self.start_frame=int(self.char_data)
			# set the time control to this value
			self.m_anim.setMinTime(OM.MTime(self.start_frame))
		## found an end frame value
		elif name == "EndFrame" :
			self.end_frame=int(self.char_data)
			# set the end animation time

		## found the number of frames
		elif name == "NumFrames" :
			self.num_frames=int(self.char_data)
		## found the vertex
		elif name =="Vertex" :
			self.char_data=self.char_data.strip()
			data=self.char_data.split(" ")
			## now we check to see if there are enough values to parse
			if len(data) == 3 :
				# append the vertex data to the array for later loading into the mesh
				self.vert_data.append(float(data[0]),float(data[1]),float(data[2]))
		elif name=="Frame" :
			# now we have the end of the frame we should have all the vertex data in the array
			# so we can set this point position for our mesh
			self.mesh.setPoints(self.vert_data)
			# once we have done this we can set this as a keyframe
			cmds.setKeyframe(breakdown=0, hierarchy="none",controlPoints=0 ,shape=0,attribute="vtx[*]")
			# now we clear the point data ready for the next frame to load hte data in
			self.vert_data.clear()



def PointBakeImport() :
	# create a promptDialog for the base group name of our mesh this will help to
	# avoid name conflicts, may be good to modify this at some stage to check if mesh
	# exists and prompt to replace data / key
	result = cmds.promptDialog(title='Name',message='Enter Name for import',button=['OK', 'Cancel'],
	defaultButton='OK',cancelButton='Cancel',dismissString='Cancel')

	# if ok was pressed lets process the data
	if result == 'OK':
		# first we get the text entered by the user
		text = cmds.promptDialog(query=True, text=True)
		# now get the obj file to import
		obj_filename=cmds.fileDialog2(caption="Please select obj file to import",fileFilter="*.obj", fm=1)

		cmds.file(obj_filename,i=True,type="OBJ",ns=text,mergeNamespacesOnClash=True)
		cmds.refresh()
		# now the xml file
		basicFilter = "*.xml"
		pointbake_file=cmds.fileDialog2(caption="Please select xml file to import",fileFilter=basicFilter, fm=1)
		# select the object imported
		print(f"Selecting {text}:*")
		cmds.select(f"{text}:*")
		name=cmds.ls(sl=True,type='transform')
		
		print (f"Debug {pointbake_file=} {text=}")
		print(f"Debug name len {len(name)} ")
		
	
		print(f"Debug {name=}")
		# and pass control back to the parser
		parser = xml.sax.make_parser()
		print(f"Debug -> calling with {name=}")
		parser.setContentHandler(ParseHandler(f"{name[0]}"))
		parser.parse(open(str(pointbake_file[0]),"r"))

PointBakeImport()