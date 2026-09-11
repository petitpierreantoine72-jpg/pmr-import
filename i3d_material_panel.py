
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


# ##### I3D_Material_Panel #####
#
#  This class is simply a container to allow us to be able to hold cache and render the UI 
#	for custom materials , note data for the materials should be  
#
# ##### END I3D_Material_Panel #####


print(__file__)

import bpy, bpy_extras
from bpy.app.handlers import persistent

import bmesh
import platform
import os.path
import re
from os import listdir
from os.path import isfile, join
from . import i3d_export
from . import dcc as dcc
from .util import i3d_directoryFinderUtil as dirf
from .util import logUtil, pathUtil, stringUtil, selectionUtil, i3d_shaderUtil
from .dcc import UINT_MAX_AS_STRING, dccBlender


import math
from mathutils import Vector, Matrix, Euler


from .tools import *


import bpy



def fixupshaderpath(value):
    try:
        if value[0] == '$':
            fullShaderPath = value
            fullShaderPath = fullShaderPath.replace("/", os.sep)
            fullShaderPath = fullShaderPath.replace("\\",os.sep)
            fullShaderPath = fullShaderPath.replace("$", bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation)
        elif os.path.isfile(value):
            fullShaderPath = pathUtil.resolvePath(value, referenceDirectory = None, targetDirectory = None)
        else:
            fullShaderPath = pathUtil.resolvePath(value, referenceDirectory = bpy.path.abspath("//"), targetDirectory = None)
    except pathUtil.InputError as e:
        return None
    
    return fullShaderPath

"""
This code looks odd when you read it at first however it is setup to work around the nature of the 
blender api. 
Our material panel is not setup like a blender panel rather it is done as just a set of ui elements with their 
own creation and rendering routines. 
What happens when we build the UI we parse the custom shader data and determine what items to build, 
any blender properties created we simply generate into a property group class definition which we then register. 
Note in theory we could create a general class with an array of items and just not render the ones not in use
however doing so sticks limits on the paramater numbers etc when with a few extra bits of code we can remove , 
also it is a pain because callbacks are binded.

Each panel is coded in a manner so that can be rebuilt at any moment. 
The Material Panel class is where all persistent data should be. 

"""


"""
I3D_OT_MaterialPanelFileSelector is just a basic file selector operator. 
operators by nature are statically declared and one can only really have one instance 
the way it then works is in context. 
so the idea of the callbacks setup as they are is so when we call to draw we can 
change the context using materialPanelID and materialCallackID to determine what callback to fire
(very icky yes)
"""
gFileSelectorCallbacks = {}

class I3D_OT_MaterialPanelFileSelector(bpy.types.Operator,bpy_extras.io_utils.ImportHelper):
    """ GUI element Button to select a Folder Path """

    bl_idname = "i3d.materialpanelfileselector"
    bl_label = "select file"
    bl_description = "find file"
    filter_glob: bpy.props.StringProperty(
        default='*.txt;*.blend',
        options={'HIDDEN'})

    materialPanelID      : bpy.props.StringProperty()
    materialCallackID     : bpy.props.StringProperty()

    def execute(self, context):

        global gFileSelectorCallbacks
        callback = gFileSelectorCallbacks.get(self.materialPanelID, {}).get(self.materialCallackID)

        if callback:
            callback(context, self.filepath, self )
  
        

        return {'FINISHED'}


"""
I3D_OT_MaterialPanelWarningPopup is just selection operator. 
operators by nature are statically declared and one can only really have one instance 
the way it then works is in context. 
so the idea of the callbacks setup as they are is so when we call to draw we can 
change the context using materialPanelID and panel_name to determine what callback to fire
(very icky yes)
"""

class I3D_OT_MaterialPanelWarningPopup(bpy.types.Operator):
    """Display a warning message"""
    bl_idname = "i3d.materialpanelwarningpopup"
    bl_label = "Warning"
    
    message: bpy.props.StringProperty()  # Property to hold the message to display
  
    def execute(self, context):
        self.report({'WARNING'}, self.message)  # Display the warning message
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


"""
I3D_MaterialSelectionUI 
This is a dialog to handle the material file selection 
It uses an emum but also has a tick box which can be used to track the active material. 
Note here I have went with trying to use prop search as it fits the requirements. 
I have tried creating several operators and will probably attempt a few more. 
However when making a custom operator I have found that the model callback is very slow
"""


class I3D_MaterialSelectionUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel

    def buildUI(self, context, _properties ):

        _parentPanel = self.m_parentPanel

        def updateTrackTick(self, context):
            nonlocal _parentPanel 
            _parentPanel.m_trackActiveMaterial = self.m_i3d_trackActiveMaterial
            _parentPanel.queueRebuild()
  
        def updateNextMaterialName(self, context):
            nonlocal _parentPanel 
            _parentPanel.setMaterialByName(self.m_i3d_nexttrackActiveMaterial)
            
        defaultmaterialname = ""
        if _parentPanel.m_materialObject != None :
            defaultmaterialname = _parentPanel.m_materialObject.name

        _properties.update(
        {
            "m_i3d_trackActiveMaterial": bpy.props.BoolProperty(name = "Track Active Material" ,default=_parentPanel.m_trackActiveMaterial, update=updateTrackTick),
             "m_i3d_nexttrackActiveMaterial": bpy.props.StringProperty(name = "Next Active Material" ,default=defaultmaterialname, update=updateNextMaterialName),
        })

        return True

    def cleanupUI(self):
        pass
    
    def isValid(self,prop_group):
        _parentPanel = self.m_parentPanel
        propValue = getattr(prop_group, "m_i3d_nexttrackActiveMaterial", "")
        if propValue != _parentPanel.m_materialObjectName :
            _parentPanel.setMaterialByName(propValue)
            return False
            
        return True

    def renderUI(self, context, layout , prop_group):
        if prop_group == None:
            return
        box = layout.box()
        row = box.row()

        _parentPanel = self.m_parentPanel

        materialName = "None"
        if _parentPanel.m_materialObject != None:
            materialName = _parentPanel.m_materialObject.name

        row.prop(prop_group, "m_i3d_trackActiveMaterial", text="Track Active Material")

        if _parentPanel.m_trackActiveMaterial:
            row.label(text=materialName)
        else:
            row.prop_search(prop_group, "m_i3d_nexttrackActiveMaterial", bpy.data, "materials", icon='MATERIAL', text="")
      
        return 


 

"""
I3D_CustomShaderSelectionUI 
This is a dialog to handle the material file selection 
It uses an emum but also has a tick box which can be used to track the active material. 
"""

class I3D_CustomShaderSelectionUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel
        self.m_shaderName = "None"

    def buildUI(self, context, _properties ):
        if self.m_parentPanel.m_materialObject == None:
            return False

        _parentPanel = self.m_parentPanel

        _uicomponent = self

        def operatorcallback(context, value , operator ):
            nonlocal _parentPanel
            if _parentPanel.m_materialObject == None:
                return

            xmlFilePath = value
            if bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation not in xmlFilePath:
                #bpy.ops.i3d.materialpanelwarningpopup('INVOKE_DEFAULT', message=f"{xmlFilePath} is not under game root")
                operator.report({'ERROR'}, f"{xmlFilePath} is not under game root")
                return

            filepath = fixupshaderpath(xmlFilePath)
            if filepath == None:
                 #bpy.ops.i3d.materialpanelwarningpopup('INVOKE_DEFAULT', message=f"{xmlFilePath} is not a shader file")
                operator.report({'ERROR'}, f"{xmlFilePath} is not a valid path")
                return

            shaderData = i3d_shaderUtil.extractXMLShaderData(xmlFilePath)
            if shaderData == None:
                #bpy.ops.i3d.materialpanelwarningpopup('INVOKE_DEFAULT', message=f"{xmlFilePath} is not a shader file")
                operator.report({'ERROR'}, f"{xmlFilePath} is not a shader file")
                return
            
            xmlFilePath = xmlFilePath.replace(bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation, "$")
            shaderName = "None"
            if "customShader" in _parentPanel.m_materialObject:      
                shaderName = _parentPanel.m_materialObject["customShader"]            
            if xmlFilePath != shaderName:
                _parentPanel.m_materialObject["customShader"] = xmlFilePath
                _uicomponent.m_shaderName = xmlFilePath
                _parentPanel.queueRebuild()


        if _parentPanel.m_MaterialClassName not in gFileSelectorCallbacks:
            gFileSelectorCallbacks[_parentPanel.m_MaterialClassName] = {}

        gFileSelectorCallbacks[_parentPanel.m_MaterialClassName]["m_shaderFileOperator"] = operatorcallback
    
        self.m_shaderName = "None"
        if "customShader" in _parentPanel.m_materialObject:
            self.m_shaderName = _parentPanel.m_materialObject["customShader"]

        return True

    def cleanupUI(self):
        pass

    def isValid(self,prop_group):
        _parentPanel = self.m_parentPanel
        shaderName = "None"
        if "customShader" in _parentPanel.m_materialObject:
            shaderName = _parentPanel.m_materialObject["customShader"]

        if shaderName != self.m_shaderName:
            return False
            
        return True

    def renderUI(self, context, layout , prop_group):
        if prop_group == None:
            return 
     
        filename = fixupshaderpath(self.m_shaderName)

        _parentPanel = self.m_parentPanel
        if _parentPanel.m_materialObject != None:
            shaderName = self.m_shaderName
            box = layout.box()
            row = box.row()
            if filename == None: 
                textmessage = self.m_shaderName + "! is not a valid file"
                row.label(text=textmessage)
                row = box.row()
            op_props = row.operator("i3d.materialpanelfileselector", icon='FILEBROWSER',text =shaderName )
            if op_props != None:
                op_props.materialPanelID=_parentPanel.m_MaterialClassName
                op_props.materialCallackID="m_shaderFileOperator"
                op_props.filter_glob ="*.xml"

       



"""
I3D_CustomMappingSelectionUI 
This is a dialog to handle the shader mapping file selection 
It uses an emum but also has a tick box which can be used to track the active material. 
"""

class I3D_CustomMappingSelectionUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel
        self.m_mappingsName = "None"

    def buildUI(self, context, _properties ):
        if self.m_parentPanel.m_materialObject == None:
            return False

        _parentPanel = self.m_parentPanel

        _uicomponent = self

        def operatorcallback(context, value , operator ):
            nonlocal _parentPanel
            if _parentPanel.m_materialObject == None:
                return

            xmlFilePath = value

            filepath = fixupshaderpath(xmlFilePath)
            if filepath == None:
                 #bpy.ops.i3d.materialpanelwarningpopup('INVOKE_DEFAULT', message=f"{xmlFilePath} is not a shader file")
                operator.report({'ERROR'}, f"{xmlFilePath} is not a valid path")
                return

            mappingData = i3d_shaderUtil.extractXMLParamaterMappingData(xmlFilePath)
            if mappingData == None:
                #bpy.ops.i3d.materialpanelwarningpopup('INVOKE_DEFAULT', message=f"{xmlFilePath} is not a shader file")
                operator.report({'ERROR'}, f"{xmlFilePath} is not a shader mapping file")
                return
            
            xmlFilePath = xmlFilePath.replace(bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation, "$")
            mappingName = "None"
            if "customMappings" in _parentPanel.m_materialObject:      
                mappingName = _parentPanel.m_materialObject["customMappings"]            
            if xmlFilePath != mappingName:
                _parentPanel.m_materialObject["customMappings"] = xmlFilePath
                _uicomponent.m_mappingsName = xmlFilePath
                _parentPanel.queueRebuild()


        if _parentPanel.m_MaterialClassName not in gFileSelectorCallbacks:
            gFileSelectorCallbacks[_parentPanel.m_MaterialClassName] = {}

        gFileSelectorCallbacks[_parentPanel.m_MaterialClassName]["m_mappingsFileOperator"] = operatorcallback
    
        self.m_mappingsName = "None"
        if "customMappings" in _parentPanel.m_materialObject:
            self.m_mappingsName = _parentPanel.m_materialObject["customMappings"]

        return True

    def cleanupUI(self):
        pass

    def isValid(self,prop_group):
        _parentPanel = self.m_parentPanel
        mappingsName = "None"
        if "customMappings" in _parentPanel.m_materialObject:
            mappingsName = _parentPanel.m_materialObject["customMappings"]

        if mappingsName != self.m_mappingsName:
            return False
            
        return True

    def renderUI(self, context, layout , prop_group):
        if prop_group == None:
            return 
     
        filename = None
        if self.m_mappingsName != None and self.m_mappingsName != "None" :
            filename = fixupshaderpath(self.m_mappingsName)

        _parentPanel = self.m_parentPanel
        if _parentPanel.m_materialObject != None:
            mappingsName = self.m_mappingsName
            box = layout.box()
            row = box.row()
            if filename == None: 
                textmessage = self.m_mappingsName + "! is not a valid file"
                row.label(text=textmessage)
                row = box.row()
            op_props = row.operator("i3d.materialpanelfileselector", icon='FILEBROWSER',text =mappingsName )
            if op_props != None:
                op_props.materialPanelID=_parentPanel.m_MaterialClassName
                op_props.materialCallackID="m_mappingsFileOperator"
                op_props.filter_glob ="*.xml"

"""
I3D_CustomShaderVariationSelectionUI 
This is a dialog to handle the shader variation 
"""
def get_index_of_variation(variations, search_term):
    for index, variation in enumerate(variations):
        if search_term in variation:
            return index  # Return the index of the tuple containing the search_term
    return 0  # Return None if the search_term is not found in any tuple

class I3D_CustomShaderVariationSelectionUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel

    def buildUI(self, context, _properties ):

        _parentPanel = self.m_parentPanel

        def getShaderVariations(self, context):
            nonlocal _parentPanel 
            variationsTuple = (("None","None","None"),)
            if _parentPanel.m_materialObject != None:
                if "customShader" in _parentPanel.m_materialObject:
                    xmlFilePath =  _parentPanel.m_materialObject["customShader"]
                    filepath = fixupshaderpath(xmlFilePath)
                    if filepath == None:
                        return variationsTuple
                    shaderData = i3d_shaderUtil.extractXMLShaderData(filepath)
                    if shaderData != None:
                        for variation in shaderData["variations"].keys():
                            variationsTuple = variationsTuple + ((variation,variation,variation),)
            return variationsTuple

        def shaderVariationSelected(self, context):
            nonlocal _parentPanel
            if _parentPanel.m_materialObject != None:
                _value = None
                if "customShaderVariation" in _parentPanel.m_materialObject:
                    _value = _parentPanel.m_materialObject["customShaderVariation"]
                
                newValueName = self.m_i3d_selectedShaderVariationUI
                if newValueName != _value:
                    if newValueName == "None":
                        if "customShaderVariation" in _parentPanel.m_materialObject:
                            del _parentPanel.m_materialObject["customShaderVariation"]
                    else:                            
                        _parentPanel.m_materialObject["customShaderVariation"] = newValueName
                    #rebuild the ui
                    _parentPanel.queueRebuild()


        defaultValue = 0 
        searchValue = "None"
        if "customShaderVariation" in _parentPanel.m_materialObject :
            defaultValue = get_index_of_variation (getShaderVariations(self,context), _parentPanel.m_materialObject["customShaderVariation"])

        if defaultValue == 0 :
            _parentPanel.m_materialObject["customShaderVariation"] = "None"

        _properties.update(
        {
            "m_i3d_selectedShaderVariationUI": bpy.props.EnumProperty(
            items=getShaderVariations,
            name="Shader Variation",
            update=shaderVariationSelected,
            default = defaultValue
            )
        })

        return True

    def cleanupUI(self):
        pass
   
   
    def isValid(self,prop_group):
        _parentPanel = self.m_parentPanel
        propValue = getattr(prop_group, "m_i3d_selectedShaderVariationUI", None)
        materialValue = None
        if "customShaderVariation" in _parentPanel.m_materialObject :
            materialValue = _parentPanel.m_materialObject["customShaderVariation"]

        if materialValue != propValue:
            return False
            
        return True

    def renderUI(self, context, layout , prop_group):
        if prop_group == None:
            return

        _parentPanel = self.m_parentPanel

        box = layout.box()
        row = box.row()
        row.prop(prop_group, "m_i3d_selectedShaderVariationUI", text="Shader Variation")


  
"""
I3D_DefaultTexturesUI 
This is a dialog to handle the shader variation 
"""
class I3D_DefaultTexturesUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel
        self.defaultTextureInfo = None
        self.m_name = ""
 
    def buildUI(self, context, _properties , defaultTextureInfo, shaderData ):

        self.defaultTextureInfo = defaultTextureInfo
        _parentPanel = self.m_parentPanel
   
        return True

    def cleanupUI(self):
        pass

    def isValid(self,prop_group):
   
        return True
    
    def renderUI(self, context, layout , prop_group):
        if prop_group == None:
            return
        
        _parentPanel = self.m_parentPanel

        if _parentPanel.m_materialObject == None:
            return 

        if "customParameter_preferDefaultTextureFromShaderNodeName" in _parentPanel.m_materialObject :
            takefromShader = _parentPanel.m_materialObject["customParameter_preferDefaultTextureFromShaderNodeName"] == "True"
 
        value = ""
        sourceText = "none"
        # logic to get string name 
        if takefromShader :
            shadervalue = i3d_shaderUtil.getMaterialShaderTextureParamFromNodeName(_parentPanel.m_materialObjectName, self.defaultTextureInfo["nodename"] )
            if shadervalue != None :
                value = shadervalue
                sourceText = "Shader Node Name"
        # this will walk up the tree finding the links 
        
        if sourceText == "none":
            shadervalue = i3d_shaderUtil.getMaterialShaderTextureParamFromLinkInputNames(_parentPanel.m_materialObjectName, self.defaultTextureInfo["inputlinks"])
            if shadervalue != None :
                value = shadervalue
                sourceText = "Shader Node Links"   
     
        row = layout.row()
        row.label(text=self.defaultTextureInfo["nodename"])
        row.label(text=sourceText)
        row.label(text=value)
       
        return 
  
"""
I3D_CustomtextureParamEditingUI 
This is a dialog to handle the shader variation 
"""
class I3D_CustomTextureParamEditingUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel
        self.defaultvalueStr = ""
        self.m_name = ""
        self.m_boolName = "" 
        self.m_paramName = ""
        self.m_searchParamaters = None

    def buildUI(self, context, _properties , name , defaultvalueStr, shaderData ):

        self.m_name = name
        _parentPanel = self.m_parentPanel
        self.defaultvalueStr = defaultvalueStr

        if _parentPanel.m_materialObject == None:
            return False

        customShaderVariation = None
        if "customShaderVariation" in _parentPanel.m_materialObject:
            customShaderVariation = _parentPanel.m_materialObject["customShaderVariation"]
            if customShaderVariation == "None":
                customShaderVariation = None

        includeGroups = ["base"]
        if customShaderVariation != None:
            variation_groups_str = shaderData["variations_groups"][customShaderVariation]
            if variation_groups_str is not None:
                includeGroups = variation_groups_str.split()
        
        parameter_group = shaderData["textures_group"][name]
        if parameter_group is None or parameter_group not in includeGroups: 
            return
        
        shaderParamMappings = None
        if "customMappings" in _parentPanel.m_materialObject:
            #take shader location to put together an absolute path
            mappingsFile = _parentPanel.m_materialObject["customMappings"]
            mappingsFilePath = os.path.normpath(os.path.join(bpy.path.abspath("//"), mappingsFile))
            if mappingsFile.startswith("$"):
                mappingsFilePath = mappingsFile
            shaderParamMappings = i3d_shaderUtil.extractXMLParamaterMappingData(mappingsFilePath)

        if shaderParamMappings != None and name in shaderParamMappings["textureblenderMaterialLinkDict"]:
            self.m_searchParamaters = shaderParamMappings["textureblenderMaterialLinkDict"][name]
        else: 
             self.m_searchParamaters = None

    
        materialParamName = "customTexture_" + name

        isTickedOn = False
      
        if materialParamName in _parentPanel.m_materialObject :
            isTickedOn = True
            materialValue = _parentPanel.m_materialObject[materialParamName]
            

        self.m_boolName = name+"Bool"
      
        def operatorcallback(context, value , operator):
            nonlocal _parentPanel
            nonlocal materialParamName

            if _parentPanel.m_materialObject == None:
                return

            textureFilePath = value
            if bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation in textureFilePath:
                #bpy.ops.i3d.materialpanelwarningpopup('INVOKE_DEFAULT', message=f"{textureFilePath} is not under game root")
                textureFilePath = textureFilePath.replace(bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation, "$")

            _parentPanel.m_materialObject[materialParamName] = textureFilePath
         
        gFileSelectorCallbacks[_parentPanel.m_MaterialClassName][materialParamName] = operatorcallback

        uicomponent = self

        def updateTick(self,context):
            nonlocal _parentPanel 
            nonlocal materialParamName 
            nonlocal uicomponent 

            # if you toggle on and off the values you are literally changing them to the default 
            if self[uicomponent.m_boolName] == True:
                _parentPanel.m_materialObject[materialParamName] = uicomponent.defaultvalueStr
            else:
                if materialParamName in _parentPanel.m_materialObject:
                    del _parentPanel.m_materialObject[materialParamName]

        _properties.update(
        {
            self.m_boolName: bpy.props.BoolProperty(name =self.m_boolName,default=isTickedOn, update=updateTick),
        })

        return True

    def cleanupUI(self):
        pass

    def isValid(self,prop_group):
        _parentPanel = self.m_parentPanel
        paramName = "customTexture_" + self.m_name

        enableText = paramName in _parentPanel.m_materialObject

        if enableText:
            # test if the tick box is off if it is refresh i.e we are invalid
            # this can happen is someone is messing with the values in the material property panel directly
            if getattr(prop_group, self.m_boolName) == False:
                return False
        else:
            # test if the tick box is off if it is refresh i.e we are invalid
            if getattr(prop_group, self.m_boolName) == True:
                return False

        return True
    
    def renderUI(self, context, layout , prop_group):
        if prop_group == None:
            return
        
        _parentPanel = self.m_parentPanel

        if _parentPanel.m_materialObject == None:
            return 

        paramName = "customTexture_" + self.m_name 

        enableText = paramName in _parentPanel.m_materialObject

        #row = layout.row()
        #row.label(text=str(self.m_defaultValue))
        row = layout.row()
        row.prop(prop_group, self.m_boolName, text="")
        if enableText : 
            row_items = row.row()
            row_items.label(text=self.m_name)
            op_props = row.operator("i3d.materialpanelfileselector", icon='TEXTURE',text =_parentPanel.m_materialObject[paramName] )
            if op_props != None:
                op_props.materialPanelID=_parentPanel.m_MaterialClassName
                op_props.materialCallackID=paramName
                op_props.filter_glob ="*.tif;*.png;*.tga;*.dds"

        else:
            row_items = row.row()
            sourceText = "default"
            value = self.defaultvalueStr
            takefromShader = False
      
            if self.m_searchParamaters != None and "customTexture_takeParamFromShaderNodeName" in _parentPanel.m_materialObject :
                takefromShader = _parentPanel.m_materialObject["customTexture_takeParamFromShaderNodeName"] == "True"
 
            if takefromShader :
                shadervalue = i3d_shaderUtil.getMaterialShaderTextureParamFromNodeName(_parentPanel.m_materialObjectName, self.m_searchParamaters)
                if shadervalue != None :
                    value = shadervalue
                    sourceText = "Shader Node Name"
 
            row_items.label(text=self.m_name)
            row_items.label(text=sourceText)
            row_items.label(text=value)

        return 



"""
I3D_CustomBufferParamEditingUI 
This is a dialog to handle the shader variation 
"""
class I3D_CustomBufferParamEditingUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel
        self.defaultvalueStr = ""
        self.m_name = ""
        self.m_boolName = "" 
        self.m_paramName = ""
        self.m_searchParamaters = None

    def buildUI(self, context, _properties , name , defaultvalueStr, shaderData ):

        self.m_name = name
        _parentPanel = self.m_parentPanel
        self.defaultvalueStr = defaultvalueStr

        if _parentPanel.m_materialObject == None:
            return False

        customShaderVariation = None
        if "customShaderVariation" in _parentPanel.m_materialObject:
            customShaderVariation = _parentPanel.m_materialObject["customShaderVariation"]
            if customShaderVariation == "None":
                customShaderVariation = None

        includeGroups = ["base"]
        if customShaderVariation != None:
            variation_groups_str = shaderData["variations_groups"][customShaderVariation]
            if variation_groups_str is not None:
                includeGroups = variation_groups_str.split()
        
        parameter_group = shaderData["buffers_group"][name]
        if parameter_group is None or parameter_group not in includeGroups: 
            return
        
        shaderParamMappings = None
        if "customMappings" in _parentPanel.m_materialObject:
            #take shader location to put together an absolute path
            mappingsFile = _parentPanel.m_materialObject["customMappings"]
            mappingsFilePath = os.path.normpath(os.path.join(bpy.path.abspath("//"), mappingsFile))
            if mappingsFile.startswith("$"):
                mappingsFilePath = mappingsFile
            shaderParamMappings = i3d_shaderUtil.extractXMLParamaterMappingData(mappingsFilePath)

        if shaderParamMappings != None and name in shaderParamMappings["bufferblenderMaterialLinkDict"]:
            self.m_searchParamaters = shaderParamMappings["bufferblenderMaterialLinkDict"][name]
        else: 
             self.m_searchParamaters = None

    
        materialParamName = "customBuffer_" + name

        isTickedOn = False
      
        if materialParamName in _parentPanel.m_materialObject :
            isTickedOn = True
            materialValue = _parentPanel.m_materialObject[materialParamName]
            

        self.m_boolName = name+"Bool"
      
        def operatorcallback(context, value , operator):
            nonlocal _parentPanel
            nonlocal materialParamName

            if _parentPanel.m_materialObject == None:
                return

            bufferFilePath = value
            if bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation in bufferFilePath:
                #bpy.ops.i3d.materialpanelwarningpopup('INVOKE_DEFAULT', message=f"{bufferFilePath} is not under game root")
                bufferFilePath = bufferFilePath.replace(bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation, "$")

            _parentPanel.m_materialObject[materialParamName] = bufferFilePath
         
        gFileSelectorCallbacks[_parentPanel.m_MaterialClassName][materialParamName] = operatorcallback

        uicomponent = self

        def updateTick(self,context):
            nonlocal _parentPanel 
            nonlocal materialParamName 
            nonlocal uicomponent 

            # if you toggle on and off the values you are literally changing them to the default 
            if self[uicomponent.m_boolName] == True:
                _parentPanel.m_materialObject[materialParamName] = uicomponent.defaultvalueStr
            else:
                if materialParamName in _parentPanel.m_materialObject:
                    del _parentPanel.m_materialObject[materialParamName]

        _properties.update(
        {
            self.m_boolName: bpy.props.BoolProperty(name =self.m_boolName,default=isTickedOn, update=updateTick),
        })

        return True

    def cleanupUI(self):
        pass

    def isValid(self,prop_group):
        _parentPanel = self.m_parentPanel
        paramName = "customBuffer_" + self.m_name

        enableText = paramName in _parentPanel.m_materialObject

        if enableText:
            # test if the tick box is off if it is refresh i.e we are invalid
            # this can happen is someone is messing with the values in the material property panel directly
            if getattr(prop_group, self.m_boolName) == False:
                return False
        else:
            # test if the tick box is off if it is refresh i.e we are invalid
            if getattr(prop_group, self.m_boolName) == True:
                return False

        return True
    
    def renderUI(self, context, layout , prop_group):
        if prop_group == None:
            return
        
        _parentPanel = self.m_parentPanel

        if _parentPanel.m_materialObject == None:
            return 

        paramName = "customBuffer_" + self.m_name 

        enableText = paramName in _parentPanel.m_materialObject

        #row = layout.row()
        #row.label(text=str(self.m_defaultValue))
        row = layout.row()
        row.prop(prop_group, self.m_boolName, text="")
        if enableText : 
            row_items = row.row()
            row_items.label(text=self.m_name)
            op_props = row.operator("i3d.materialpanelfileselector", icon='TEXTURE',text =_parentPanel.m_materialObject[paramName] )
            if op_props != None:
                op_props.materialPanelID=_parentPanel.m_MaterialClassName
                op_props.materialCallackID=paramName
                op_props.filter_glob ="*.bin"

        else:
            row_items = row.row()
            sourceText = "default"
            value = self.defaultvalueStr
            takefromShader = False
      
            if self.m_searchParamaters != None and "customBuffer_takeParamFromShaderNodeName" in _parentPanel.m_materialObject :
                takefromShader = _parentPanel.m_materialObject["customBuffer_takeParamFromShaderNodeName"] == "True"
 
            if takefromShader :
                shadervalue = i3d_shaderUtil.getMaterialShaderBufferParamFromNodeName(_parentPanel.m_materialObjectName, self.m_searchParamaters)
                if shadervalue != None :
                    value = shadervalue
                    sourceText = "Shader Node Name"
 
            row_items.label(text=self.m_name)
            row_items.label(text=sourceText)
            row_items.label(text=value)

        return
"""
I3D_CustomFloatParamEditingUI 
This is a dialog to handle the shader variation 
"""
class I3D_CustomFloatParamEditingUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel
        self.m_defaultValue = ""
        self.m_name = ""
        self.m_boolName = "" 
        self.m_paramName = ""
        self.m_searchParamaters = None 

    def buildUI(self, context, _properties , name , defaultvalueStr, shaderData ):

        self.m_name = name
        _parentPanel = self.m_parentPanel
        self.defaultvalueStr = defaultvalueStr

        if _parentPanel.m_materialObject == None:
            return False

        customShaderVariation = None
        if "customShaderVariation" in _parentPanel.m_materialObject:
            customShaderVariation = _parentPanel.m_materialObject["customShaderVariation"]
            if customShaderVariation == "None":
                customShaderVariation = None

        includeGroups = ["base"]
        if customShaderVariation != None:
            variation_groups_str = shaderData["variations_groups"][customShaderVariation]
            if variation_groups_str is not None:
                includeGroups = variation_groups_str.split()
        
        parameter_group = shaderData["parameters_group"][name]
        if parameter_group is None or parameter_group not in includeGroups: 
            return
        
        # first thing lets get the number of elements 
        _numberElements = 0
        # this is a little numpty but it works 
        paramType = shaderData["parameterTypes"][name]
        if paramType == 'float4':
            _numberElements = 4
        elif paramType == 'float3':
             _numberElements = 3
        elif paramType == 'float2':
            _numberElements = 2
        elif paramType == 'float':
            _numberElements = 1

        if _numberElements == 0: 
            return false

        self.m_numberOfElements = _numberElements

        defaultvalue = []
        try:
            tempvalue = [float(x) for x in defaultvalueStr.strip().split(" ")]
            defaultvalue[:] = tempvalue[:min(_numberElements,len(tempvalue))]
        except Exception as e:
            defaultvalue = []
            for x in range(_numberElements):    
                defaultvalue.append(1)


        shaderParamMappings = None
        if "customMappings" in _parentPanel.m_materialObject:
            #take shader location to put together an absolute path
            mappingsFile = _parentPanel.m_materialObject["customMappings"]
            mappingsFilePath = os.path.normpath(os.path.join(bpy.path.abspath("//"), mappingsFile))
            if mappingsFile.startswith("$"):
                mappingsFilePath = mappingsFile
            shaderParamMappings = i3d_shaderUtil.extractXMLParamaterMappingData(mappingsFilePath)

        if shaderParamMappings != None and name in shaderParamMappings["paramatersblenderMaterialLinkDict"]:
            self.m_searchParamaters = shaderParamMappings["paramatersblenderMaterialLinkDict"][name]
        else: 
             self.m_searchParamaters = None


        #to do work on min and max
       
        self.m_defaultValue = defaultvalue
        uiValue = defaultvalue[:]
        isTickedOn = False

        materialParamName = "customParameter_" + name

        uicomponent = self

      
        if materialParamName in _parentPanel.m_materialObject :
            isTickedOn = True
            materialValue = [float(x) for x in _parentPanel.m_materialObject[materialParamName].strip().split(" ")]
            uiValue[:] = materialValue[:min(len(uiValue),len(materialValue))]
            # fix the thing back up
            stringValue = " ".join(f"{value:.3f}" for value in uiValue)
            _parentPanel.m_materialObject[materialParamName] = stringValue

        self.m_boolName = name+"Bool"
        self.m_paramName = name+"Param"

        def updateTick(self,context):
            nonlocal _parentPanel 
            nonlocal materialParamName 
            nonlocal uicomponent 

            # if you toggle on and off the values you are literally changing them to the default 
            if self[uicomponent.m_boolName] == True:
                self[uicomponent.m_paramName] = uicomponent.m_defaultValue
                stringValue = " ".join(f"{value:.3f}" for value in self[uicomponent.m_paramName])
                _parentPanel.m_materialObject[materialParamName] = stringValue
            else:
                if materialParamName in _parentPanel.m_materialObject:
                    del _parentPanel.m_materialObject[materialParamName]


        def valueUpdate(self,context):
            nonlocal _parentPanel 
            nonlocal materialParamName 
            nonlocal uicomponent
       
            if materialParamName in _parentPanel.m_materialObject:
               stringValue = " ".join(f"{value:.3f}" for value in self[uicomponent.m_paramName])
               _parentPanel.m_materialObject[materialParamName] = stringValue
    

        _properties.update(
        {
            self.m_boolName: bpy.props.BoolProperty(name =self.m_boolName,default=isTickedOn, update=updateTick),
            self.m_paramName: bpy.props.FloatVectorProperty(
                name=self.m_paramName,
                description="float param",
                default=uiValue,  
                size=_numberElements, 
                update=valueUpdate,  # Link to the update function 
                precision = 3 
                )
        })

        return True

    def cleanupUI(self):
        pass

    def isValid(self,prop_group):
        _parentPanel = self.m_parentPanel
        paramName = "customParameter_" + self.m_name

        enableText = paramName in _parentPanel.m_materialObject

        if enableText:
            # test if the tick box is off if it is refresh i.e we are invalid
            # this can happen is someone is messing with the values in the material property panel directly
            if getattr(prop_group, self.m_boolName) == False:
                return False

            floatvalue = getattr(prop_group, self.m_paramName)
            stringValue = " ".join(f"{value:.3f}" for value in floatvalue)
            if _parentPanel.m_materialObject[paramName] != stringValue:
                return False
        else:
            # test if the tick box is off if it is refresh i.e we are invalid
            if getattr(prop_group, self.m_boolName) == True:
                return False

        return True
    
    def renderUI(self, context, layout , prop_group):
        if prop_group == None:
            return
        
        _parentPanel = self.m_parentPanel

        if _parentPanel.m_materialObject == None:
            return 

        paramName = "customParameter_" + self.m_name 

        enableText = paramName in _parentPanel.m_materialObject

        #row = layout.row()
        #row.label(text=str(self.m_defaultValue))
        row = layout.row()
        row.prop(prop_group, self.m_boolName, text="")
        if enableText : 
            row_items = row.row()
            row_items.prop(prop_group,self.m_paramName, text=self.m_name)


        else:
            row_items = row.row()
            sourceText = "default"
            value = self.m_defaultValue[:]
            takefromShader = False
      
            if "customParameter_takeParamFromShaderNodeName" in _parentPanel.m_materialObject and self.m_searchParamaters != None:
                takefromShader = _parentPanel.m_materialObject["customParameter_takeParamFromShaderNodeName"] == "True"
 
            if takefromShader :
                shadervalue = i3d_shaderUtil.getMaterialShaderFloatParam(_parentPanel.m_materialObjectName, self.m_searchParamaters, self.m_numberOfElements)
                if shadervalue != None :
                    value = shadervalue
                    sourceText = "Shader Node Name"
 
            row_items.label(text=self.m_name)
            row_items.label(text=sourceText)
            stringValue = ""
            if isinstance(value, float) :
                stringValue = "{:.3f}".format(value)
            else :
                stringValue = " ".join(f"{part:.3f}" for part in value)
            row_items.label(text=stringValue)

        return 

class I3D_TakeParamFromShaderNodeNameUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel
        self.m_paramName = None
        self.m_message = None

    def buildUI(self, context, _properties , paramName , message):

        self.m_paramName = paramName; 
        _parentPanel = self.m_parentPanel
        _paramName = self.m_paramName
        self.m_message = message

        def getValueVariations(self, context):
            nonlocal _parentPanel 
            variationsTuple = (("False","False","False"),("True","True","True"))
            return variationsTuple

        def shaderValueTypeSelected(self, context):
            nonlocal _parentPanel
            nonlocal _paramName
            if _parentPanel.m_materialObject != None:
                newValueName = "True" if self[_paramName] == 1 else "False"
                _parentPanel.m_materialObject[_paramName] = newValueName
               
        defaultValue = 0 
        if _paramName in _parentPanel.m_materialObject :
            defaultValue = get_index_of_variation (getValueVariations(self,context), _parentPanel.m_materialObject[_paramName])

        if defaultValue == 0 :
            _parentPanel.m_materialObject[_paramName] = "False"

        _properties.update(
        {
            _paramName: bpy.props.EnumProperty(
            items=getValueVariations,
            name=_paramName,
            update=shaderValueTypeSelected,
            default = defaultValue
            )
        })

        return True

    def cleanupUI(self):
        pass
   
   
    def isValid(self,prop_group):
        _parentPanel = self.m_parentPanel
        propValue = getattr(prop_group, self.m_paramName, None)
        materialValue = None
        if self.m_paramName in _parentPanel.m_materialObject :
            materialValue = _parentPanel.m_materialObject[self.m_paramName]

        if materialValue != propValue:
            return False
            
        return True

    def renderUI(self, context, layout , prop_group):
        if prop_group == None:
            return

        _parentPanel = self.m_parentPanel

        box = layout.box()
        row = box.row()
        row.prop(prop_group, self.m_paramName, text=self.m_message)
  
"""
class for shading rate. 
"""        
class I3D_ShadingRateUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel

    def buildUI(self, context, _properties ):

        _parentPanel = self.m_parentPanel

        def getShadingRateValueVariations(self, context):
            variationsTuple = ( ('1x1' ,  '1x1'   ,  '1x1'),
                          ('1x2',  '1x2', '1x2'),
                          ('2x1',  '2x1', '2x1'),
                          ('2x2',  '2x2', '2x2'),
                          ('2x4',  '2x4', '2x4'),
                          ('4x2',  '4x2', '4x2'),
                          ('4x4',  '4x4', '4x4'))
            return variationsTuple

        def shaderRateValueTypeSelected(self, context):
            nonlocal _parentPanel
            if _parentPanel.m_materialObject != None:
                newValueName = self.m_shadingRate
                _parentPanel.m_materialObject["shadingRate"] = newValueName
               
        defaultValue = 0 
        if "shadingRate" in _parentPanel.m_materialObject :
            defaultValue = get_index_of_variation (getShadingRateValueVariations(self,context), _parentPanel.m_materialObject["shadingRate"])
        else :
            _parentPanel.m_materialObject["shadingRate"] = '1x1'

        _properties.update(
        {
            "m_shadingRate": bpy.props.EnumProperty(
            items=getShadingRateValueVariations,
            name="m_shadingRate",
            update=shaderRateValueTypeSelected,
            default = defaultValue
            )
        })

        return True

    def cleanupUI(self):
        pass
   
   
    def isValid(self,prop_group):
        _parentPanel = self.m_parentPanel
        propValue = getattr(prop_group, "m_shadingRate", None)
        materialValue = None
        if "shadingRate" in _parentPanel.m_materialObject :
            materialValue = _parentPanel.m_materialObject["shadingRate"]

        if materialValue != propValue:
            return False
            
        return True

    def renderUI(self, context, layout , prop_group):
        if prop_group == None:
            return

        _parentPanel = self.m_parentPanel

        box = layout.box()
        row = box.row()
        row.prop(prop_group, "m_shadingRate", text="Shading Rate")



"""
class for render flags (Alpha blending, doublsided)
"""        
class I3D_RenderFlagsUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel
        self.m_doubleSided = _parentPanel.m_materialObject.use_backface_culling == False
        self.m_alphaBlending = _parentPanel.m_materialObject.blend_method  == 'BLEND'

    def buildUI(self, context, _properties ):

        _materialObject = self.m_parentPanel.m_materialObject
        _panel = self

        def updateDoubleSized(self,context):
            nonlocal _materialObject
            nonlocal _panel
            _panel.m_doubleSided = self.m_doubleSided
            if _panel.m_doubleSided :
                _materialObject.use_backface_culling = False
            else :
                _materialObject.use_backface_culling = True

        def updateAlphaBlend(self,context):
            nonlocal _materialObject
            nonlocal _panel
            _panel.m_alphaBlending = self.m_alphaBlending
            if _panel.m_alphaBlending :
                _materialObject.blend_method = 'BLEND'
            else :
                _materialObject.blend_method = 'OPAQUE'


        _properties.update(
        {
            "m_alphaBlending": bpy.props.BoolProperty(
            name= "alphaBlending",
            update= updateAlphaBlend,
            default = self.m_alphaBlending
            ),
            "m_doubleSided": bpy.props.BoolProperty(
            name= "doubleSided",
            update= updateDoubleSized,
            default = self.m_doubleSided
            )
        })

        return True

    def cleanupUI(self):
        pass
   
   
    def isValid(self,prop_group):        
        if self.m_doubleSided == self.m_parentPanel.m_materialObject.use_backface_culling:
            return False 

        if self.m_alphaBlending == False:
            if self.m_parentPanel.m_materialObject.blend_method  == 'BLEND':
                return False
        else:
            if self.m_parentPanel.m_materialObject.blend_method  != 'BLEND':
                return False
        
        return True

    def renderUI(self, context, layout , prop_group):
        if prop_group == None:
            return

        _parentPanel = self.m_parentPanel

        box = layout.box()
        row = box.row()
        row.prop(prop_group, "m_alphaBlending", text="Alpha Blending")
        row = box.row()
        row.prop(prop_group, "m_doubleSided", text="Double Sided")
  

"""
class handling refractions 
"""

class I3D_RenderRefractionUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel
        self.m_useRefraction = False
        self.m_refractionCoeff = 1.0
        self.m_refractionBumpScale = 0.05

    def buildUI(self, context, _properties):
        _materialObject = self.m_parentPanel.m_materialObject
        _panel = self

        def updateUseRefraction(self, context):
            nonlocal _materialObject
            if _materialObject:
                if self.m_useRefraction == False: 
                    del _materialObject["customParameter_useRefraction"]
                    del _materialObject["customParameter_refractionCoeff"]
                    del _materialObject["customParameter_refractionBumpScale"]
                else:
                    _materialObject["customParameter_useRefraction"] = True
                    _materialObject["customParameter_refractionCoeff"] = self.m_refractionCoeff
                    _materialObject["customParameter_refractionBumpScale"] = self.m_refractionBumpScale

        def updateRefractionCoeff(self, context):
            nonlocal _materialObject
            if _materialObject:
                _materialObject["customParameter_refractionCoeff"] = self.m_refractionCoeff

        def updateRefractionBumpScale(self, context):
            nonlocal _materialObject
            nonlocal _panel
            if _materialObject:
                _materialObject["customParameter_refractionBumpScale"] = self.m_refractionBumpScale

        # Initialize properties with material values if they exist
        if _materialObject:
            self.m_useRefraction = _materialObject.get("customParameter_useRefraction", False)
            if self.m_useRefraction :
                if "customParameter_refractionCoeff" in _materialObject:
                    self.m_refractionCoeff = _materialObject["customParameter_refractionCoeff"]
                else :
                    self.m_refractionCoeff = _materialObject["customParameter_refractionCoeff"] = 1.0

                if "customParameter_refractionCoeff" in _materialObject:
                    self.m_refractionBumpScale = _materialObject["customParameter_refractionBumpScale"]
                else :
                    self.m_refractionBumpScale = _materialObject["customParameter_refractionBumpScale"] = 0.1

        _properties.update({
            "m_useRefraction": bpy.props.BoolProperty(
                name="Enable Refraction",
                update=updateUseRefraction,
                default=self.m_useRefraction
            ),
            "m_refractionCoeff": bpy.props.FloatProperty(
                name="Refraction Coefficient",
                update=updateRefractionCoeff,
                default=self.m_refractionCoeff,
                min=0.0, max=1.0
            ),
            "m_refractionBumpScale": bpy.props.FloatProperty(
                name="Refraction Bump Scale",
                update=updateRefractionBumpScale,
                default=self.m_refractionBumpScale,
                min=0.0, max=10.0
            )
        })

        return True

    def cleanupUI(self):
        pass


    def isValid(self,prop_group):
        _parentPanel = self.m_parentPanel
   
        enableRefraction = False
        if "customParameter_useRefraction" in _parentPanel.m_materialObject:
            if _parentPanel.m_materialObject["customParameter_useRefraction"] :
                enableRefraction = True

        if enableRefraction:
            # test if the tick box is off if it is refresh i.e we are invalid
            # this can happen is someone is messing with the values in the material property panel directly
            if getattr(prop_group, "m_useRefraction") == False:
                return False

            if "customParameter_refractionCoeff" not in _parentPanel.m_materialObject:
                return False

            floatvalue = getattr(prop_group, "m_refractionCoeff")
            if floatvalue != _parentPanel.m_materialObject["customParameter_refractionCoeff"] :
                return False

    
            if "customParameter_refractionCoeff" not in _parentPanel.m_materialObject:
                return False

            floatvalue = getattr(prop_group, "m_refractionBumpScale")
            if floatvalue != _parentPanel.m_materialObject["customParameter_refractionBumpScale"] :
                return False

        else:
            # test if the tick box is off if it is refresh i.e we are invalid
            if getattr(prop_group, "m_useRefraction") == True:
                return False

        return True


    def renderUI(self, context, layout, prop_group):
        if not prop_group:
            return

        box = layout.box()
        row = box.row()
        row.prop(prop_group, "m_useRefraction", text="Enable Refraction")

        if prop_group.m_useRefraction:
            col = box.column()
            col.prop(prop_group, "m_refractionCoeff", text="Refraction Coefficient")
            col.prop(prop_group, "m_refractionBumpScale", text="Refraction Bump Scale")
            
            


"""
class handling reflections
"""
class I3D_RenderReflectionUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel
        self.m_useReflection = False

    def buildUI(self, context, _properties):
        _materialObject = self.m_parentPanel.m_materialObject
        _panel = self

        def updateUseReflection(self, context):
            nonlocal _materialObject
            if _materialObject:
                if self.m_useReflection == False: 
                    del _materialObject["customParameter_useReflection"]
                else:
                    _materialObject["customParameter_useReflection"] = True

        # Initialize properties with material values if they exist
        if _materialObject:
            self.m_useReflection = _materialObject.get("customParameter_useReflection", False)

        _properties.update({
            "m_useReflection": bpy.props.BoolProperty(
                name="Enable Reflection",
                update=updateUseReflection,
                default=self.m_useReflection
            ),
        })

        return True

    def cleanupUI(self):
        pass


    def isValid(self,prop_group):
        _parentPanel = self.m_parentPanel
   
        enableReflection = False
        if "customParameter_useReflection" in _parentPanel.m_materialObject:
            if _parentPanel.m_materialObject["customParameter_useReflection"] :
                enableReflection = True

        if enableReflection:
            # test if the tick box is off if it is refresh i.e we are invalid
            # this can happen is someone is messing with the values in the material property panel directly
            if getattr(prop_group, "m_useReflection") == False:
                return False
        else :
             if getattr(prop_group, "m_useReflection") == True:
                return False
        return True


    def renderUI(self, context, layout, prop_group):
        if not prop_group:
            return

        box = layout.box()
        row = box.row()
        row.prop(prop_group, "m_useReflection", text="Enable Reflection")

#-------------------------------------------------------------------------------

"""
class for aggregating all the elements. 
every element in the UI is its own class 
"""
class I3D_Material_Panel:

    sMaterialPanelID = 0
 
 
    def __init__(self):
        # Initialization code here (if necessary)
        self.m_UIElements = []

        # items for material selection as noted they are in this panel as they persist
        # the idea is we rebuild the ui elements everytime we need to and they render based on what has been meantioned
        self.m_trackActiveMaterial = False
        self.m_materialObject = None
        self.m_materialObjectName = ""
        self.m_materialPanelPropertiesClass = None
        self.m_alphaBlending = False
        I3D_Material_Panel.sMaterialPanelID = I3D_Material_Panel.sMaterialPanelID+1
        self.m_panelId = I3D_Material_Panel.sMaterialPanelID
        self.m_MaterialClassName = "I3D_Material_Panel" + str(self.m_panelId)
        self.m_rebuildRequests = 1
        # register the panel with the update loop
        if bpy.app.timers.is_registered(self.updateLoop) == False:
            bpy.app.timers.register(self.updateLoop)

    def __del__(self):
         if bpy.app.timers.is_registered(self.updateLoop):
            bpy.app.timers.unregister(self.updateLoop)
 
    def handlePostLoad(self):
        #print("handlepostload")
        self.m_materialObjectName = ""
        self.m_materialObject = None
        self.queueRebuild()
        if bpy.app.timers.is_registered(self.updateLoop) == False:
            bpy.app.timers.register(self.updateLoop)
            print("reset update loop after load")
 
        
        return 0.1

    def cleanupUI(self,context):
        for item in self.m_UIElements:
            item.cleanupUI()

        self.m_UIElements.clear()
        # Register the dynamically created PropertyGroup
        if self.m_materialPanelPropertiesClass != None:
            bpy.utils.unregister_class(self.m_materialPanelPropertiesClass)
            self.m_materialPanelPropertiesClass = None
           
        if hasattr(bpy.types.Scene, self.m_MaterialClassName):
            delattr(bpy.types.Scene, self.m_MaterialClassName)

        global gFileSelectorCallbacks
        if self.m_MaterialClassName in gFileSelectorCallbacks:
            del gFileSelectorCallbacks[self.m_MaterialClassName]

 

    def buildUI(self,context):

        if self.m_materialPanelPropertiesClass != None:
            return

        #this is the most effective way to clean out all caches which happen too much
        I3D_Material_Panel.sMaterialPanelID = I3D_Material_Panel.sMaterialPanelID+1
        self.m_panelId = I3D_Material_Panel.sMaterialPanelID
        self.m_MaterialClassName = "I3D_Material_Panel" + str(self.m_panelId)
 
        materialPanel = self
 
        properties = {}

        selectedMaterialUI = I3D_MaterialSelectionUI(materialPanel)
        if selectedMaterialUI.buildUI(context,properties) :
            self.m_UIElements.append(selectedMaterialUI)

        if materialPanel.m_materialObject != None :
            # build the other UI panels now
            customShaderUI = I3D_CustomShaderSelectionUI(materialPanel)
            if customShaderUI.buildUI(context,properties) :
                self.m_UIElements.append(customShaderUI)

            shaderParamMappings = None
            if "customMappings" in self.m_materialObject:
                #take shader location to put together an absolute path
                mappingsFile = self.m_materialObject["customMappings"]
                mappingsFilePath = os.path.normpath(os.path.join(bpy.path.abspath("//"), mappingsFile))
                if mappingsFile.startswith("$"):
                    mappingsFilePath = mappingsFile
                shaderParamMappings = i3d_shaderUtil.extractXMLParamaterMappingData(mappingsFilePath)


            # start building property UI
            if "customShader" in materialPanel.m_materialObject:
                xmlFilePath =  materialPanel.m_materialObject["customShader"]
                filepath = fixupshaderpath(xmlFilePath)
                if filepath != None:
                    shaderData = i3d_shaderUtil.extractXMLShaderData(filepath)
                    if shaderData:
                        # lets make the shader variation panel
                        customShaderVariationUI = I3D_CustomShaderVariationSelectionUI(materialPanel)
                        if customShaderVariationUI.buildUI(context,properties) :
                            self.m_UIElements.append(customShaderVariationUI)

                        customMappingSelectionUI = I3D_CustomMappingSelectionUI(materialPanel)
                        if customMappingSelectionUI.buildUI(context,properties) :
                            self.m_UIElements.append(customMappingSelectionUI)

                        renderFlagsUI = I3D_RenderFlagsUI(materialPanel)
                        if renderFlagsUI.buildUI(context,properties) :
                            self.m_UIElements.append(renderFlagsUI)

                        refractionUI = I3D_RenderRefractionUI(materialPanel)
                        if refractionUI.buildUI(context,properties) :
                            self.m_UIElements.append(refractionUI)

                        reflectionUI = I3D_RenderReflectionUI(materialPanel)
                        if reflectionUI.buildUI(context,properties) :
                            self.m_UIElements.append(reflectionUI)

                   
                        if shaderParamMappings != None:
                            customtakefromShaderUI = I3D_TakeParamFromShaderNodeNameUI(materialPanel)
                            if customtakefromShaderUI.buildUI(context,properties, "customParameter_takeParamFromShaderNodeName" , "Take param values from shader node names") :
                                self.m_UIElements.append(customtakefromShaderUI)

                        # now lets build the parameters
                        for name, defaultvalue in shaderData["parameters"].items():
                            customShaderParamUI = I3D_CustomFloatParamEditingUI(materialPanel)
                            if customShaderParamUI.buildUI(context,properties,name,defaultvalue, shaderData) :
                                self.m_UIElements.append(customShaderParamUI)
    

                        # now lets put in the default textures 
                        customtakefromShaderUI = I3D_TakeParamFromShaderNodeNameUI(materialPanel)
                        if customtakefromShaderUI.buildUI(context,properties,"customParameter_preferDefaultTextureFromShaderNodeName" , "Prefer default textures from node names") :
                            self.m_UIElements.append(customtakefromShaderUI)

                        for key, defaulttextureinfo in shaderData["defaultTextures"].items():
                            defaultTextureUI = I3D_DefaultTexturesUI(materialPanel)
                            if defaultTextureUI.buildUI(context,properties, defaulttextureinfo, shaderData) :
                                self.m_UIElements.append(defaultTextureUI)


                        # now lets build the custom textures
                        if shaderParamMappings != None:
                            customtakefromShaderUI = I3D_TakeParamFromShaderNodeNameUI(materialPanel )
                            if customtakefromShaderUI.buildUI(context,properties,"customTexture_takeParamFromShaderNodeName" , "Take param values from shader node names") :
                                self.m_UIElements.append(customtakefromShaderUI)
                        for name, defaultvalue in shaderData["textures"].items():
                            customShaderTextureParamUI = I3D_CustomTextureParamEditingUI(materialPanel)
                            if customShaderTextureParamUI.buildUI(context,properties,name,defaultvalue, shaderData) :
                                self.m_UIElements.append(customShaderTextureParamUI)

                        # now lets build the custom buffers
                        if shaderParamMappings != None:
                            customtakefromShaderUI = I3D_TakeParamFromShaderNodeNameUI(materialPanel )
                            if customtakefromShaderUI.buildUI(context,properties,"customBuffer_takeParamFromShaderNodeName" , "Take param values from shader node names") :
                                self.m_UIElements.append(customtakefromShaderUI)
                        for name, defaultvalue in shaderData["buffers"].items():
                            customShaderTextureParamUI = I3D_CustomBufferParamEditingUI(materialPanel)
                            if customShaderTextureParamUI.buildUI(context,properties,name,defaultvalue, shaderData) :
                                self.m_UIElements.append(customShaderTextureParamUI)


                        customShadingRateUI = I3D_ShadingRateUI(materialPanel)
                        if customShadingRateUI.buildUI(context,properties) :
                            self.m_UIElements.append(customShadingRateUI)

              

        # Dynamically create the PropertyGroup class
        self.m_materialPanelPropertiesClass = type(
            self.m_MaterialClassName,
            (bpy.types.PropertyGroup,),
            {'__annotations__': properties}
        )

        

        try:
            # Register the dynamically created PropertyGroup
            bpy.utils.register_class(self.m_materialPanelPropertiesClass)
            if not hasattr(bpy.types.Scene, self.m_MaterialClassName):  # Check if not already added
                ptr = bpy.props.PointerProperty(type=self.m_materialPanelPropertiesClass)
                setattr(bpy.types.Scene, self.m_MaterialClassName, ptr)
                self.m_Properties = getattr(bpy.types.Scene, self.m_MaterialClassName)
        except Exception as e:
            print("Could not add class {} to scene".format(self.m_materialPanelPropertiesClass))
            print(e)
        
 
    
    def rebuildUI(self,context):
        self.cleanupUI(context)
        self.buildUI(context)
        # force a redraw
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

    def queueRebuild(self):
        self.m_rebuildRequests =  self.m_rebuildRequests+1
      
    def setMaterialByName(self, materialObjName):
        if self.m_materialObjectName != materialObjName:
            self.m_materialObjectName = materialObjName
            self.queueRebuild()

 
    def updateLoop(self):
        try:
            context = bpy.context

            # first are we tracking 
            if self.m_trackActiveMaterial:
                active_mat = context.object.active_material
                if active_mat:
                    self.m_materialObjectName = active_mat.name
                else: 
                    self.m_materialObjectName = ""
            
            newMaterialObject = None
            if self.m_materialObjectName != "None" and len(self.m_materialObjectName) > 0 :
                if self.m_materialObjectName in bpy.data.materials:
                    newMaterialObject = bpy.data.materials[self.m_materialObjectName]
            
            if newMaterialObject != self.m_materialObject:
                self.m_materialObject = newMaterialObject
                self.m_rebuildRequests =  self.m_rebuildRequests+1           

        
            if self.m_rebuildRequests == 0 :
                scene = context.scene
                prop_group = None
                # Assuming property group is attached under a dynamic name
                if hasattr(scene, self.m_MaterialClassName):
                    prop_group = getattr(scene, self.m_MaterialClassName)
                if prop_group != None:
                    for item in self.m_UIElements:
                        if item.isValid(prop_group) == False:
                            self.m_rebuildRequests =  self.m_rebuildRequests+1 
                            break

            # if there has been any rebuild requests then lets rebuild
            if self.m_rebuildRequests > 0:
                self.rebuildUI(context)
                self.m_rebuildRequests = 0

        except Exception as e:
            print("Exception Hit")
            print(e)

        #print("update complete")
        return 0.1

    def draw(self, context , layout):
        # Here, you add the specific UI elements you need
        path = context.scene.I3D_UIexportSettings.I3D_gameLocationDisplay
        if os.path.exists(path) == False:
            box = layout.box()
            row = box.row()
            row.label(text="No game folder set")
            return


        # validate the material. 
        # this is needed because if you do not do this it will crash esp with undo and redo
        newMaterialObject = None
        if self.m_materialObjectName != "None" and len(self.m_materialObjectName) > 0 :
            newMaterialObject = bpy.data.materials[self.m_materialObjectName]
            
        if newMaterialObject != self.m_materialObject:
            row.label(text="Need refresh")
            self.queueRebuild()
            return

        scene = context.scene

        prop_group = None
        # Assuming your property group is attached under a dynamic name
        if hasattr(scene, self.m_MaterialClassName):
            prop_group = getattr(scene, self.m_MaterialClassName)
      
        if prop_group == None:
            return

        for item in self.m_UIElements:
            item.renderUI(context, layout , prop_group)
        


classes = [I3D_OT_MaterialPanelFileSelector,
           I3D_OT_MaterialPanelWarningPopup]

def registerMaterialPanelItems():
    for cls in classes:
        bpy.utils.register_class(cls)
 
def unregisterMaterialPanelItems():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    # Additional teardown can go here

