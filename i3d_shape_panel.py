
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

from .dcc.dccBlender import I3D_CustomShapeAttributes

import math
from mathutils import Vector, Matrix, Euler


from .tools import *


def fixupshapeattributepath(value):
    try:
        if value[0] == '$':
            fullshapefilePath = value
            fullshapefilePath = fullshapefilePath.replace("/", os.sep)
            fullshapefilePath = fullshapefilePath.replace("\\",os.sep)
            fullShaderPath = fullshapefilePath.replace("$", bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation)
        elif os.path.isfile(value):
            fullshapefilePath = pathUtil.resolvePath(value, referenceDirectory = None, targetDirectory = None)
        else:
            fullshapefilePath = pathUtil.resolvePath(value, referenceDirectory = bpy.path.abspath("//"), targetDirectory = None)
    except pathUtil.InputError as e:
        return None
    
    return fullshapefilePath


"""
I3D_OT_ShapePanelFileSelector is just a basic file selector operator. 
operators by nature are statically declared and one can only really have one instance 
the way it then works is in context. 
so the idea of the callbacks setup as they are is so when we call to draw we can 
change the context using materialPanelID and materialCallackID to determine what callback to fire
(very icky yes)
"""
gShapeFileSelectorCallbacks = {}

class I3D_OT_ShapePanelFileSelector(bpy.types.Operator,bpy_extras.io_utils.ImportHelper):
    """ GUI element Button to select a Folder Path """

    bl_idname = "i3d.shapepanelfileselector"
    bl_label = "select file"
    bl_description = "find file"
    filter_glob: bpy.props.StringProperty(
        default='*.txt;*.xml',
        options={'HIDDEN'})

    shapePanelID      : bpy.props.StringProperty()
    shapeCallbackID     : bpy.props.StringProperty()

    def execute(self, context):

        global gShapeFileSelectorCallbacks
        callback = gShapeFileSelectorCallbacks.get(self.shapePanelID, {}).get(self.shapeCallbackID)

        if callback:
            callback(context, self.filepath, self )
  
        

        return {'FINISHED'}

"""
I3D_customShapeAttributesFileelectionUI 
This is a dialog to handle the shader mapping file selection 
It uses an emum but also has a tick box which can be used to track the active material. 
"""

class I3D_customShapeAttributesFileselectionUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel
        self.m_mappingsName = "None"

    def buildUI(self, context, _properties ):
        if self.m_parentPanel.m_meshObject == None:
            return False

        _parentPanel = self.m_parentPanel

        _uicomponent = self

        def operatorcallback(context, value , operator ):
            nonlocal _parentPanel
            if _parentPanel.m_meshObject == None:
                return

            xmlFilePath = value

            filepath = fixupshapeattributepath(xmlFilePath)
            if filepath == None:
                 #bpy.ops.i3d.materialpanelwarningpopup('INVOKE_DEFAULT', message=f"{xmlFilePath} is not a shader file")
                operator.report({'ERROR'}, f"{xmlFilePath} is not a valid path")
                return

            mappingData = I3D_CustomShapeAttributes.load_from_xml(xmlFilePath)
            if mappingData == None:
                #bpy.ops.i3d.materialpanelwarningpopup('INVOKE_DEFAULT', message=f"{xmlFilePath} is not a shader file")
                operator.report({'ERROR'}, f"{xmlFilePath} is not a shape attribute mapping file")
                return
            
            xmlFilePath = xmlFilePath.replace(bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation, "$")
            mappingName = "None"
            if "customShapeAttributesFile" in _parentPanel.m_meshObject:      
                mappingName = _parentPanel.m_meshObject["customShapeAttributesFile"]            
            if xmlFilePath != mappingName:
                _parentPanel.m_meshObject["customShapeAttributesFile"] = xmlFilePath
                _uicomponent.m_mappingsName = xmlFilePath
                _parentPanel.queueRebuild()


        if _parentPanel.m_ShapeDefinitionClassName not in gShapeFileSelectorCallbacks:
            gShapeFileSelectorCallbacks[_parentPanel.m_ShapeDefinitionClassName] = {}

        gShapeFileSelectorCallbacks[_parentPanel.m_ShapeDefinitionClassName]["m_mappingsFileOperator"] = operatorcallback
    
        self.m_mappingsName = "None"
        if "customShapeAttributesFile" in _parentPanel.m_meshObject:
            self.m_mappingsName = _parentPanel.m_meshObject["customShapeAttributesFile"]

        return True

    def cleanupUI(self):
        pass

    def isValid(self,prop_group):
        _parentPanel = self.m_parentPanel
        mappingsName = "None"
        if "customShapeAttributesFile" in _parentPanel.m_meshObject:
            mappingsName = _parentPanel.m_meshObject["customShapeAttributesFile"]

        if mappingsName != self.m_mappingsName:
            return False
            
        return True

    def renderUI(self, context, layout , prop_group):
        if prop_group == None:
            return 
     
        filename = None
        if self.m_mappingsName != None and self.m_mappingsName != "None" :
            filename = fixupshapeattributepath(self.m_mappingsName)

        _parentPanel = self.m_parentPanel
        if _parentPanel.m_meshObject != None:
            mappingsName = self.m_mappingsName
            box = layout.box()
            row = box.row()
            if filename == None: 
                textmessage = self.m_mappingsName + "! is not a valid file"
                row.label(text=textmessage)
                row = box.row()
            op_props = row.operator("i3d.shapepanelfileselector", icon='FILEBROWSER',text =mappingsName )
            if op_props != None:
                op_props.shapePanelID=_parentPanel.m_ShapeDefinitionClassName
                op_props.shapeCallbackID="m_mappingsFileOperator"
                op_props.filter_glob ="*.xml"

"""
I3D_MaterialSelectionUI 
This is a dialog to handle the material file selection 
It uses an emum but also has a tick box which can be used to track the active material. 
Note here I have went with trying to use prop search as it fits the requirements. 
I have tried creating several operators and will probably attempt a few more. 
However when making a custom operator I have found that the model callback is very slow
"""


class I3D_MeshSelectionUI:
    def __init__(self, _parentPanel):
        self.m_parentPanel = _parentPanel

    def buildUI(self, context, _properties ):

        _parentPanel = self.m_parentPanel

        def updateTrackTick(self, context):
            nonlocal _parentPanel 
            _parentPanel.m_trackActiveMesh = self.m_i3d_trackActiveMesh
            _parentPanel.queueRebuild()
  
        def updateNextMeshName(self, context):
            nonlocal _parentPanel 
            _parentPanel.setMeshByName(self.m_i3d_nexttrackActiveMesh)
            
        defaultmeshname = ""
        if _parentPanel.m_meshObject != None :
            defaultmeshname = _parentPanel.m_meshObject.name

        _properties.update(
        {
            "m_i3d_trackActiveMesh": bpy.props.BoolProperty(name = "Track Active Mesh" ,default=_parentPanel.m_trackActiveMesh, update=updateTrackTick),
             "m_i3d_nexttrackActiveMesh": bpy.props.StringProperty(name = "Next Active Mesh" ,default=defaultmeshname, update=updateNextMeshName),
        })

        return True

    def cleanupUI(self):
        pass
    
    def isValid(self,prop_group):
        _parentPanel = self.m_parentPanel
        propValue = getattr(prop_group, "m_i3d_nexttrackActiveMesh", "")
        if propValue != _parentPanel.m_meshObjectName :
            _parentPanel.setMeshByName(propValue)
            return False
            
        return True

    def renderUI(self, context, layout , prop_group):
        if prop_group == None:
            return
        box = layout.box()
        row = box.row()

        _parentPanel = self.m_parentPanel

        meshName = "None"
        if _parentPanel.m_meshObject != None:
            meshName = _parentPanel.m_meshObject.name

        row.prop(prop_group, "m_i3d_trackActiveMesh", text="Track Active Mesh")

        if _parentPanel.m_trackActiveMesh:
            row.label(text=meshName)
        else:
            row.prop_search(prop_group, "m_i3d_nexttrackActiveMesh", bpy.data, "meshes", icon='MESH_DATA', text="")
      
        return 




class I3D_ShapeDefinition_Panel:

    sShapeDefinitionPanelID = 0
 
 
    def __init__(self):
        # Initialization code here (if necessary)
        self.m_UIElements = []

        # items for ShapeDefinition selection as noted they are in this panel as they persist
        # the idea is we rebuild the ui elements everytime we need to and they render based on what has been meantioned
        self.m_trackActiveMesh = False
        self.m_meshObject = None
        self.m_meshObjectName = ""
        self.m_ShapeDefinitionPanelPropertiesClass = None
        I3D_ShapeDefinition_Panel.sShapeDefinitionPanelID = I3D_ShapeDefinition_Panel.sShapeDefinitionPanelID+1
        self.m_panelId = I3D_ShapeDefinition_Panel.sShapeDefinitionPanelID
        self.m_ShapeDefinitionClassName = "I3D_ShapeDefinition_Panel" + str(self.m_panelId)
        self.m_rebuildRequests = 1
        # register the panel with the update loop
        if bpy.app.timers.is_registered(self.updateLoop) == False:
            bpy.app.timers.register(self.updateLoop)

    def __del__(self):
         if bpy.app.timers.is_registered(self.updateLoop):
            bpy.app.timers.unregister(self.updateLoop)
 
    def handlePostLoad(self):
        #print("handlepostload")
        self.m_meshObjectName = ""
        self.m_meshObject = None
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
        if self.m_ShapeDefinitionPanelPropertiesClass != None:
            bpy.utils.unregister_class(self.m_ShapeDefinitionPanelPropertiesClass)
            self.m_ShapeDefinitionPanelPropertiesClass = None
           
        if hasattr(bpy.types.Scene, self.m_ShapeDefinitionClassName):
            delattr(bpy.types.Scene, self.m_ShapeDefinitionClassName)

        global gShapeFileSelectorCallbacks
        if self.m_ShapeDefinitionClassName in gShapeFileSelectorCallbacks:
            del gShapeFileSelectorCallbacks[self.m_ShapeDefinitionClassName]

 

    def buildUI(self,context):

        if self.m_ShapeDefinitionPanelPropertiesClass != None:
            return

        #this is the most effective way to clean out all caches which happen too much
        I3D_ShapeDefinition_Panel.sShapeDefinitionPanelID = I3D_ShapeDefinition_Panel.sShapeDefinitionPanelID+1
        self.m_panelId = I3D_ShapeDefinition_Panel.sShapeDefinitionPanelID
        self.m_ShapeDefinitionClassName = "I3D_ShapeDefinition_Panel" + str(self.m_panelId)
 
        ShapeDefinitionPanel = self
 
        properties = {}
        selectedShapeDefinitionUI = I3D_MeshSelectionUI(ShapeDefinitionPanel)
        if selectedShapeDefinitionUI.buildUI(context,properties) :
            self.m_UIElements.append(selectedShapeDefinitionUI)

        if ShapeDefinitionPanel.m_meshObject != None :
            # build the other UI panels now
            fileselectUI = I3D_customShapeAttributesFileselectionUI(ShapeDefinitionPanel)
            if fileselectUI.buildUI(context,properties) :
                self.m_UIElements.append(fileselectUI)

            customShapeAttributesFile = None
            if "customShapeAttributesFile" in self.m_meshObject:
                #take shader location to put together an absolute path
                mappingsFile = self.m_meshObject["customShapeAttributesFile"]
                mappingsFilePath = os.path.normpath(os.path.join(bpy.path.abspath("//"), mappingsFile))
                if mappingsFile[0] == "$":
                        mappingsFilePath = mappingsFile
                customShapeAttributesFile = I3D_CustomShapeAttributes.load_from_xml(mappingsFilePath)
              
        
        # Dynamically create the PropertyGroup class
        self.m_ShapeDefinitionPanelPropertiesClass = type(
            self.m_ShapeDefinitionClassName,
            (bpy.types.PropertyGroup,),
            {'__annotations__': properties}
        )

        

        try:
            # Register the dynamically created PropertyGroup
            bpy.utils.register_class(self.m_ShapeDefinitionPanelPropertiesClass)
            if not hasattr(bpy.types.Scene, self.m_ShapeDefinitionClassName):  # Check if not already added
                ptr = bpy.props.PointerProperty(type=self.m_ShapeDefinitionPanelPropertiesClass)
                setattr(bpy.types.Scene, self.m_ShapeDefinitionClassName, ptr)
                self.m_Properties = getattr(bpy.types.Scene, self.m_ShapeDefinitionClassName)
        except Exception as e:
            print("Could not add class {} to scene".format(self.m_ShapeDefinitionPanelPropertiesClass))
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
      
    def setMeshByName(self, meshName):
        if self.m_meshObjectName != meshName:
            self.m_meshObjectName = meshName
            self.queueRebuild()

 
    def updateLoop(self):
        try:
            context = bpy.context

            # first are we tracking 
            if self.m_trackActiveMesh:
                active_object = context.active_object
                if active_object and active_object.type == 'MESH':
                    self.m_meshObjectName = active_object.data.name
                else:
                    self.m_meshObjectName = ""
            
            newMeshObject = None
            if self.m_meshObjectName != "None" and len(self.m_meshObjectName) > 0 :
                if self.m_meshObjectName in bpy.data.meshes:
                    newMeshObject = bpy.data.meshes[self.m_meshObjectName]
            
            if newMeshObject != self.m_meshObject:
                self.m_meshObject = newMeshObject
                self.m_rebuildRequests =  self.m_rebuildRequests+1           

        
            if self.m_rebuildRequests == 0 :
                scene = context.scene
                prop_group = None
                # Assuming property group is attached under a dynamic name
                if hasattr(scene, self.m_ShapeDefinitionClassName):
                    prop_group = getattr(scene, self.m_ShapeDefinitionClassName)
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


        # validate the ShapeDefinition. 
        # this is needed because if you do not do this it will crash esp with undo and redo
        newShapeDefinitionObject = None
        if self.m_meshObjectName != "None" and len(self.m_meshObjectName) > 0 :
            newShapeDefinitionObject = bpy.data.meshes[self.m_meshObjectName]
            
        if newShapeDefinitionObject != self.m_meshObject:
            row.label(text="Need refresh")
            self.queueRebuild()
            return

        scene = context.scene

        prop_group = None
        # Assuming your property group is attached under a dynamic name
        if hasattr(scene, self.m_ShapeDefinitionClassName):
            prop_group = getattr(scene, self.m_ShapeDefinitionClassName)
      
        if prop_group == None:
            return

        for item in self.m_UIElements:
            item.renderUI(context, layout , prop_group)


classes = [I3D_OT_ShapePanelFileSelector
           ]

def registerShapePanelItems():
    for cls in classes:
        bpy.utils.register_class(cls)
 
def unregisterShapePanelItems():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    # Additional teardown can go here