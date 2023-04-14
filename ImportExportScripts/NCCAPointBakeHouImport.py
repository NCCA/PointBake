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
import hou
import xml.sax
import os
import shutil
import sys

"""@package docstring
This module will allow the selection of an obj file and a xml based NCCA Point bake file and
load in point baked animation to a houdini scene. The user is prompted for a base node name
which is pre-pended to all elements create in the loading process, It is recommended that the
data is exported as a clip file once loaded as this will be more efficient.

@author Jonathan Macey
@version 1.0
@date Last Revision 10/01/11 fixed bug in xml parse

 previous updates :

 Updated to NCCA Coding standard

"""


########################################################################################################################
##  @brief a basic function to return a file name / absolute path stripping off $HIP etc
##	@param[in] title the title to be displayed in the file box
##  @param[in] wildCard the file selection wildcard i.e. *.obj etc
##  @param[in] fileType the houdini file type option e.g. hou.fileType.Any
##  @returns a fully qualified file path or None
########################################################################################################################

def GetAbsoluteFileName(title,wildCard,fileType) :
	# launch a file select and get the data
	file=hou.ui.selectFile(None,title,False,fileType,wildCard)
	# if it was empty bomb out and return none
	if file =="" :
		return None
	else :
		# so we got some data we need to split it as we could have $JOB $HIP or $HOME prepended
		# to it  if we partition based on the / we get a tuple with "", "/","/....." where the
		# first element is going to be an environment var etc.
		file=file.partition("/")
		# we have $HOME so extract the full $HOME path and use it
		if file[0]=="$HOME" :
			prefix=str(hou.getenv("HOME"))
		elif file[0] == "$HIP" :
		#we have $HIP so extract the full $HIP path
			prefix=str(hou.getenv("HIP"))
		# we have a $JOB so extract the full $JOB path
		elif file[0] == "$JOB" :
			prefix=str(hou.getenv("JOB"))
		# nothing so just blank the string
		else :
			prefix=str("")
	#now construct our new file name from the elements we've found
	return "%s/%s" %(prefix,file[2])

## \class ParseHandler
## @brief a class to wrap the processing of the xml.sax parser, all of the methods are called
## from this class however the class data is specific to the parsing process. In this case it is a
## parser for the NCCA PointBake file format


class ParseHandler(xml.sax.ContentHandler):

	## @brief ctor for the class passing in the houdini channel we wish to load the
	## PB data into
	## @param[in] chan the channel that the parsed xml data should be loaded too
	def init(self,chan):
		## @brief the Character Data stored as part of parsing
		self.mcharData=""
		## @brief the mmeshName extracted from the PointBake file
		self.mmeshName=""
		## @brief number of vertices in the mesh, we will check this against the number of points in
		## the mesh / obj loaded as a basic compatibility check
		self.mnumVerts=0
		## @brief the Start frame for the data loaded
		self.mstartFrame=0
		## @brief mendFrame of the data loaded
		self.mendFrame=0
		## @brief number of frames stored in file not used in this example
		self.mnumFrames=0
		## @brief the Channel used for assigning the data from the xml file passed to the parser
		## when constructed
		self.mchannel=chan
		## @brief the Offset into the vertex list for the current data to be set too
		self.moffset=None
		## @brief the Current frame to be stored / keyed
		self.mcurrentFrame=0


	def del(self) :
		hou.ui.setStatusMessage("Finished Import",hou.severityType.Message)

	## @brief here we trigger events for the start elements In this case we grab the Offset and Frame
	## @param[in] name the name of the tag to process
	## @param[in] attrs the attribute associated with the current tag
	def startElement(self, name, attrs):
		# this is important the characters method may be called many times so we
		# clear the char data each start element then append each time we read it
		self.mcharData=""
		# if we have a vertex start tag process and extract the offset
		if name == "Vertex" :
			self.moffset=int(attrs.get("number"))
		# if we have the Frame we grab the number attribute
		elif name == "Frame" :
			hou.setFrame(int(attrs.get("number")))
			self.mcurrentFrame=int(attrs.get("number"))

	## @brief trigger method if we have data between the <> </> tags, copy it to the class mcharData so
	## we can re-use it later
	## \param[in] content the character string passed from the parser.
	def characters(self,content):
		# here we append the content data passed into the method, we need to append
		# as this function may be called more than once if we have a long string
		self.mcharData += content

	## @brief most of the hard processing is done here. Once an end tag is encountered we
	## process the current char data and add it to the channel created. This does
	## rely on the order of the data but this is always machine generated so we should
	## be safe if it does go wrong it will be this data ordering
	## @brief[in] name the name of the end element tag
	def endElement(self, name):
		# extract the mmeshName and save it
		if name == "MeshName":
			self.mmeshName=self.mcharData
		# get the number of vertices and set this to the channel
		elif name == "NumVerts" :
			# store value
			self.mnumVerts=int(self.mcharData)

			# now set the Channel to have this number of channels (may be large)
			self.mchannel.parm("numchannels").set(self.mnumVerts)
			# now we traverse all the elements and re-size to 3 and rename the data to a translate
			# we need to change this later for other attribute types (rot etc etc)
			for i in range(0,self.mnumVerts) :
				channel.parm("size%d" %(i)).set(3)
				channel.parm("name%d" %(i)).set("t")
		# parse and sel the mstartFrame
		elif name == "StartFrame" :
			self.mstartFrame=int(self.mcharData)
			self.mchannel.parm("start").set(self.mstartFrame)
		## found an end frame value
		elif name == "EndFrame" :
			self.mendFrame=int(self.mcharData)
			self.mchannel.parm("end").set(self.mendFrame)
		## found the number of frames
		elif name == "NumFrames" :
			self.mnumFrames=int(self.mcharData)
		## found the vertex
		elif name =="Vertex" :
			hou.ui.setStatusMessage("Processing Frame %d channel %d" %(self.mcurrentFrame,self.moffset),hou.severityType.Message)
			self.mcharData=self.mcharData.strip()
			data=self.mcharData.split(" ")
			## now we check to see if there are enough values to parse
			if len(data) == 3 :
				houparmtuple = self.mchannel.parmTuple("value%d" %(self.moffset))
				houkeyframe = hou.Keyframe()
				houkeyframe.setExpression(str(data[0]), hou.exprLanguage.Hscript)
				houparmtuple[0].setKeyframe(houkeyframe)
				houkeyframe.setExpression(str(data[1]), hou.exprLanguage.Hscript)
				houparmtuple[1].setKeyframe(houkeyframe)
				houkeyframe.setExpression(str(data[2]), hou.exprLanguage.Hscript)
				houparmtuple[2].setKeyframe(houkeyframe)


objectFile=GetAbsoluteFileName("Select Object File","*.obj",hou.fileType.Geometry)
if(objectFile==None) :
    sys.exit()
bakeFile=GetAbsoluteFileName("Select Bake File","*.xml",hou.fileType.Any)
if(bakeFile==None) :
    sys.exit()

## @brief baseName is used to store the prefix name used for all created nodes
baseName=hou.ui.readInput("Enter Base Node Name")
## @brief we now copy this to a new string
baseName=baseName[1]

## @brief scene is used to store a reference to the scene when we change to the scene level
scene=hou.cd("/scene")
## @brief create our geo node and then attache the correct file to it.
geo=hou.node("/obj").createNode("geo")
geo.setName("%sObjectImport" %(baseName))
## @brief grab our file node so we can set the correct file name
file=hou.node('/obj/%sObjectImport/file1' %(baseName))
file.parm("file").set(objectFile)
## @brief  now create a chopnet for this geo and attach the channel
chopnet=geo.createNode("chopnet")
chopnet.setName("%sBakeChannel" %(baseName))
## @brief now we create our channel in the chop net this will be modified by the parser
channel=chopnet.createNode("channel")
## @brief due to the way the data is created we need to have a re-name node to change the format
rename=chopnet.createNode("rename")
rename.parm("renamefrom").set("?[xyz]")
rename.parm("renameto").set("t[xyz]0")
rename.setName("%sRename" %(baseName))
rename.setFirstInput(channel)
channel.setName("%sImportData" %(baseName))
## @brief the geoChan node is used to link the channel in the chopnet to the geo
geoChan=geo.createNode("channel");
geoChan.parm("choppath").set("/obj/%sObjectImport/%sBakeChannel/%sRename" %(baseName,baseName,baseName))
geoChan.parm("chanscope").set("t[xyz]")
geoChan.parm("method").set(1)
# now connect the channel to the file node
geoChan.setFirstInput(file)
geoChan.setDisplayFlag(True)

parser = xml.sax.makeparser()
parser.setContentHandler(ParseHandler(channel))
parser.parse(open(bakeFile,"r"))