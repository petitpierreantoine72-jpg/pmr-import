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
from .util import logUtil, pathUtil, stringUtil, selectionUtil, i3d_shaderUtil , meshchoppingUtil
from .dcc import UINT_MAX_AS_STRING, dccBlender
import cProfile
import pstats

import math
from mathutils import Vector, Matrix, Euler


from .tools import *

from .i3d_material_panel import *

from .i3d_shape_panel import *


gS4MaterialPanel = I3D_Material_Panel();
gS4ShapePanel = I3D_ShapeDefinition_Panel();

#trying to use lxml package. Fallback is standard xml package
g_usingLXML = True
try:
    from lxml import etree as xml_ET
except:
    import xml.etree.cElementTree as xml_ET
    g_usingLXML = False

g_dynamicGUIClsDict = {}
g_modalsRunning = False

#g_materialTemplateThumbnails = None
g_loadedMaterialTemplates = {'templates': {}}
g_selectedMaterialTemplateCategory = None
g_disableTemplatedParameterUpdatedCallback = False
g_disableParameterTemplateSelectedCallback = False
g_disableSelectedMaterialEnumUpdateCallback = False

g_collisionFiltersData = i3d_export.I3DCollisionFilters()

def extractXMLShaderData():
    dirPath = bpy.context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation
    #dirPath = bpy.path.abspath(dirPath)
    fileName = bpy.context.scene.I3D_UIexportSettings.I3D_shaderEnum
    
    xmlFile = dirPath + os.sep + fileName

    return i3d_shaderUtil.extractXMLShaderData(xmlFile)

def toggleAutoAssign(self, context):
    if self.UI_autoAssign:
        # dcc.I3DSaveObjectAttributes()
        dcc.I3DLoadObjectAttributes()
    else:
        dcc.I3DSaveObjectAttributes()

def updateCollisionFilters(self, context):
    presetName = self.I3D_collisionFilterPreset

    if presetName in g_collisionFiltersData.presets:
        preset = g_collisionFiltersData.presets[presetName]
        self["I3D_collisionFilterGroup"] = preset.group
        self["I3D_collisionFilterMask"] = preset.mask
    else:
        self.I3D_collisionFilterPreset = "-"
        self["I3D_collisionFilterGroup"] = 0
        self["I3D_collisionFilterMask"] = 0

def updateFromPredefinePhysic(self, context):
    """Update function if a predefined Setting is selected"""

    predefineName = self.I3D_predefinedPhysic
    if predefineName == 'NONE':
        return
    for key, value in dcc.I3DgetPredefinePhysicAttr(predefineName).items():
        self[key] = value
    context.scene.I3D_UIexportSettings.I3D_selectedPredefined = [tup[1] for tup in dcc.UIgetPredefinePhysicItems(self,context) if tup[0] == predefineName][0]
    self.I3D_predefinedPhysic = 'NONE'

def updateFromPredefineNonPhysic(self, context):
    """Update function if a predefined Setting is selected"""

    predefineName = self.I3D_predefinedNonPhysic
    if predefineName == 'NONE':
        return
    for key, value in dcc.I3DgetPredefineNonPhysicAttr(predefineName).items():
        self[key] = value
    context.scene.I3D_UIexportSettings.I3D_selectedPredefined = [tup[1] for tup in dcc.UIgetPredefineNonPhysicItems(self,context) if tup[0] == predefineName][0]
    self.I3D_predefinedNonPhysic = 'NONE'

def lightUseShadowUpdate(self, context):
    softShadowParams = [
        "I3D_softShadowsLightSize",
        "I3D_softShadowsLightDistance",
        "I3D_softShadowsDepthBiasFactor",
        "I3D_softShadowsMaxPenumbraSize"
    ]
    if not self.UI_lightUseShadow:
        for softShadowParam in softShadowParams:
            setattr(self, softShadowParam, dcc.SETTINGS_ATTRIBUTES[softShadowParam]['defaultValue'])
    else:
        node = self.I3D_nodeName
        nodeData = bpy.data.objects[node]
        for softShadowParam in softShadowParams:
            if softShadowParam in nodeData:
                setattr(self, softShadowParam, nodeData[softShadowParam])
            else:
                setattr(self, softShadowParam, dcc.SETTINGS_ATTRIBUTES[softShadowParam]['defaultValue'])

def setExportRelativePath(self, context):
    """Update function for dynamic GUI behavior"""

    if self.I3D_exportGameRelativePath:
        # self.I3D_exportRelativePaths = True
        pass

def setGameRelativePath(self,context):
    if not self.I3D_exportRelativePaths:
        # self.I3D_exportGameRelativePath = False
        pass

def updateShaderFolderLocation(context):
    """ Sets the currently defined shader folder location to be relative to the game location, if
    it is set, or to an absolute path otherwise. """
    if gS4MaterialPanel != None:
        gS4MaterialPanel.queueRebuild()

    if gS4ShapePanel != None:
        gS4ShapePanel.queueRebuild()

    path = context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation
    if path is None or path == "" or path[0] == "$":
        return

    if context.scene.I3D_UIexportSettings.I3D_gameLocation is not None and context.scene.I3D_UIexportSettings.I3D_gameLocation != "":
        path = "$" + os.path.relpath(path, start = context.scene.I3D_UIexportSettings.I3D_gameLocation)
    else:
        path = os.path.abspath(path)
    context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation = path
    


def setGameLocationPath(self,context):
    """ Set game location path and the representative path """

    path = context.scene.I3D_UIexportSettings.I3D_gameLocationDisplay
    if os.path.exists(path):
        context.scene.I3D_UIexportSettings.I3D_gameLocation = path
        updateShaderFolderLocation(context)
    else:
        shaderPath = context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation
        if shaderPath != None and shaderPath != "" and shaderPath[0] == "$":
            context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation = context.scene.I3D_UIexportSettings.I3D_gameLocation + context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation[1:]
        context.scene.I3D_UIexportSettings.I3D_gameLocation = ""

        self.report({'WARNING'},"{} is not a valid path".format(path))

def onWriteShaderPath(self,context):

    if not context.scene.I3D_UIexportSettings.I3D_shaderEnum in [t[0] for t in I3D_PT_PanelExport.getShadersFromDirectory(self,context)]:
        context.scene.I3D_UIexportSettings.I3D_shaderEnum = [t[0] for t in I3D_PT_PanelExport.getShadersFromDirectory(self,context)][0]

def boundingVolumeMergeGroupUpdate(self,context):
    context.scene.I3D_UIexportSettings.I3D_boundingVolume = context.scene.I3D_UIexportSettings.I3D_boundingVolumeMergeGroup

def selectedMaterialEnumUpdate(self, context):
    if g_disableSelectedMaterialEnumUpdateCallback:
        return

    # Select all objects which have the chosen material assigned.
    mat = self.I3D_selectedMaterialEnum
    [obj.select_set(mat in [materialSlot.material.name for materialSlot in obj.material_slots]) for obj in bpy.data.objects]

def templatedParameterEnabled(self, context, parameterTemplateId, subTemplateId, paramName):
    # Reset the template for this parameter if the checkbox is unset.
    if not getattr(self, paramName + "Bool"):
        setattr(self, "templatedParameterTemplateMenu_" + parameterTemplateId + "_" + paramName, "None")

def templatedParameterEnableCallback(parameterTemplateId, subTemplateId, paramName):
    return lambda self, context : templatedParameterEnabled(self, context, parameterTemplateId, subTemplateId, paramName)

def templatedParameterUpdated(self, context, parameterTemplateId, subTemplateId, paramName):
    global g_disableTemplatedParameterUpdatedCallback

    if g_disableTemplatedParameterUpdatedCallback:
        return
    
    setattr(self, "templatedParameterTemplateMenu_" + parameterTemplateId + "_" + paramName, "None")

def templatedParameterUpdateCallback(parameterTemplateId, subTemplateId, paramName):
    return lambda self, context : templatedParameterUpdated(self, context, parameterTemplateId, subTemplateId, paramName)

def templateForParameterSelected(self, context, parameterTemplateId, subTemplateId, paramName):
    global g_disableTemplatedParameterUpdatedCallback

    shaderData = extractXMLShaderData()

    parameterTemplateDict = shaderData["parameterTemplates"][parameterTemplateId]
    subTemplateDict = parameterTemplateDict["subtemplates"][subTemplateId]
    selectedTemplateName = getattr(self, "templatedParameterTemplateMenu_" + parameterTemplateId + "_" + paramName)

    if selectedTemplateName in subTemplateDict["templates"]:
        selectedTemplate = subTemplateDict["templates"][selectedTemplateName]

        value = selectedTemplate[paramName]
        try:
            valueList = [float(x) for x in value.strip().split(" ")]
        except Exception as e:
            # TODO(jdellsperger): Inform about malformed xml?
            valueList = parameterTemplateDict["parameters"][paramName]
        valueList = valueList + [1.0,1.0,1.0,1.0]

        g_disableTemplatedParameterUpdatedCallback = True
        setattr(self, paramName + "_0", valueList[0])
        setattr(self, paramName + "_1", valueList[1])
        setattr(self, paramName + "_2", valueList[2])
        setattr(self, paramName + "_3", valueList[3])
        g_disableTemplatedParameterUpdatedCallback = False

def templateForParameterSelectedCallback(parameterTemplateId, subTemplateId, paramName):
    return lambda self, context : templateForParameterSelected(self, context, parameterTemplateId, subTemplateId, paramName)

def parameterTemplateSelected(self, context, parameterTemplateId, subTemplateId):
    global g_disableParameterTemplateSelectedCallback

    if g_disableParameterTemplateSelectedCallback:
        return

    shaderData = extractXMLShaderData()
    if not shaderData:
        print("parameterTemplateSelected: no shader data")
        return
    
    if parameterTemplateId not in shaderData["parameterTemplates"]:
        print("parameterTemplateSelected: invalid parameterTemplateId")
        return
    
    parameterTemplateDict = shaderData["parameterTemplates"][parameterTemplateId]
    if subTemplateId not in parameterTemplateDict["subtemplates"]:
        print("parameterTemplateSelected: invalid subTemplateId")
        return
    
    g_disableParameterTemplateSelectedCallback = True
    
    parametersToHandle = [paramName for paramName, _ in parameterTemplateDict["parameters"].items() if not self.get(paramName + "Bool")]
    texturesToHandle = [textureName for textureName, _ in parameterTemplateDict["textures"].items() if not self.get(textureName + "Bool")]

    # Unset checkboxes for all other subtemplates.
    for k, _ in parameterTemplateDict["subtemplates"].items():
        if k != subTemplateId:
            setattr(self, k + "Bool", False)
            setattr(self, k + "_Template", "None")

    # Reset selected template if checkbox is unchecked.
    if not getattr(self, subTemplateId + "Bool"):
        setattr(self, subTemplateId + "_Template", "None")

    while subTemplateId is not None:
        subTemplateDict = parameterTemplateDict["subtemplates"][subTemplateId]
        
        selectedSubTemplateName = getattr(self, subTemplateId + "_Template")
        if selectedSubTemplateName not in subTemplateDict["templates"]:
            print("parameterTemplateSelected: invalid selectedSubTemplateName {}".format(selectedSubTemplateName))
            g_disableParameterTemplateSelectedCallback = False
            return
        
        selectedTemplate = subTemplateDict["templates"][selectedSubTemplateName]

        parametersHandledBySubTemplate = [paramName for paramName in parametersToHandle if paramName in selectedTemplate]
        parametersToHandle = [paramName for paramName in parametersToHandle if paramName not in selectedTemplate]
        for paramName in parametersHandledBySubTemplate:
            value = selectedTemplate[paramName]
            try:
                valueList = [float(x) for x in value.strip().split(" ")]
            except Exception as e:
                # TODO(jdellsperger): Inform about malformed xml?
                valueList = parameterTemplateDict["parameters"][paramName]
            valueList = valueList + [1.0,1.0,1.0,1.0]

            setattr(self, paramName + "_0", valueList[0])
            setattr(self, paramName + "_1", valueList[1])
            setattr(self, paramName + "_2", valueList[2])
            setattr(self, paramName + "_3", valueList[3])

        texturesHandledBySubTemplate = [textureName for textureName in texturesToHandle if textureName in selectedTemplate]
        texturesToHandle = [textureName for textureName in texturesToHandle if textureName not in selectedTemplate]
        for textureName in texturesHandledBySubTemplate:
            setattr(self, textureName, selectedTemplate[textureName])
        
        subTemplateId = subTemplateDict["parentId"]
        if subTemplateId is not None:
            if self.get(subTemplateId + "Bool"):
                selectedSubTemplateName = self.get(subTemplateId + "_Template")
            elif "parentTemplate" in selectedTemplate:
                selectedSubTemplateName = selectedTemplate["parentTemplate"]
                setattr(self, subTemplateId + "_Template", selectedSubTemplateName)
            else:
                selectedSubTemplateName = subTemplateDict["defaultParentTemplate"]
                setattr(self, subTemplateId + "_Template", selectedSubTemplateName)

    g_disableParameterTemplateSelectedCallback = False

def parameterTemplateSelectedCallback(parameterTemplateId, subTemplateId):
    return lambda self, context : parameterTemplateSelected(self, context, parameterTemplateId, subTemplateId)

def updateDynamicUIClassesForShaderParameters(shaderData, variation_groups):
    # Custom Parameters
    dynamicGUIDict = {}
    for paramName, value in shaderData["parameters"].items():
        # Only show parameters that share a group with the variation.
        parameter_group = shaderData["parameters_group"][paramName]
        if parameter_group not in variation_groups:
            continue

        try:
            valueList = [float(x) for x in value.strip().split(" ")]
        except Exception as e:
            print(e)
            valueList = []
        valueList = valueList + [1.0,1.0,1.0,1.0]
        dynamicGUIDict.update({
                paramName + "Bool": bpy.props.BoolProperty(name = paramName+"Bool",default=False),
                paramName + "_0": bpy.props.FloatProperty(default = valueList[0] , precision = dcc.FLOAT_PRECISION ),
                paramName + "_1": bpy.props.FloatProperty(default = valueList[1] , precision = dcc.FLOAT_PRECISION ),
                paramName + "_2": bpy.props.FloatProperty(default = valueList[2] , precision = dcc.FLOAT_PRECISION ),
                paramName + "_3": bpy.props.FloatProperty(default = valueList[3] , precision = dcc.FLOAT_PRECISION )
        })
    paramClss = type('I3D_UIShaderParameters', (bpy.types.PropertyGroup,), {'__annotations__': dynamicGUIDict})
    bpy.utils.register_class(paramClss)
    bpy.types.Scene.I3D_UIShaderParameters = bpy.props.PointerProperty(type=paramClss)

    # Custom Textures
    dynamicGUIDict = {}
    for textureName, value in shaderData["textures"].items():
        # Only show textures that share a group with the variation.
        texture_group = shaderData["textures_group"][textureName]
        if texture_group not in variation_groups:
            continue

        dynamicGUIDict.update({
                textureName + "Bool": bpy.props.BoolProperty(name=textureName, default=False),
                textureName: bpy.props.StringProperty(default=value)
                })
    textClss = type('I3D_UIShaderTextures', (bpy.types.PropertyGroup,), {'__annotations__': dynamicGUIDict})
    bpy.utils.register_class(textClss)
    bpy.types.Scene.I3D_UIShaderTextures = bpy.props.PointerProperty(type=textClss)
    g_dynamicGUIClsDict["parameters"] = paramClss
    g_dynamicGUIClsDict["textures"] = textClss

    # Parameter templates.
    for parameterTemplateId, parameterTemplate in shaderData["parameterTemplates"].items():
        dynamicGUIDict = {}
        for subtemplateId, subtemplate in parameterTemplate["subtemplates"].items():
            enums = [(templateName, templateName, '') for templateName, template in subtemplate["templates"].items()]
            enums.insert(0, ("None", "None", ""))
            dynamicGUIDict.update({
                subtemplateId + "Bool": bpy.props.BoolProperty(name = subtemplateId+"Bool", update = parameterTemplateSelectedCallback(parameterTemplateId, subtemplateId), default = False),
                subtemplateId + "_Template": bpy.props.EnumProperty(name = subtemplate["name"], items=enums, update = parameterTemplateSelectedCallback(parameterTemplateId, subtemplateId))
            })

        rootSubTemplateId = parameterTemplate["rootSubTemplateId"]
        rootTemplates = [("None", "None", "")]
        rootTemplates = rootTemplates + [(templateName, templateName, "") for templateName, _ in parameterTemplate["subtemplates"][rootSubTemplateId]["templates"].items()]
        for paramName, value in parameterTemplate["parameters"].items():
            # Only show parameters that share a group with the variation.
            parameter_group = shaderData["parameters_group"][paramName]
            if parameter_group not in variation_groups:
                continue

            try:
                valueList = [float(x) for x in value.strip().split(" ")]
            except Exception as e:
                print(e)
                valueList = []
            valueList = valueList + [1.0,1.0,1.0,1.0]
            dynamicGUIDict.update({
                paramName+"Bool": bpy.props.BoolProperty(name = paramName+"Bool",default=False),
                paramName+"_0": bpy.props.FloatProperty(default = valueList[0] , precision = dcc.FLOAT_PRECISION ),
                paramName+"_1": bpy.props.FloatProperty(default = valueList[1] , precision = dcc.FLOAT_PRECISION ),
                paramName+"_2": bpy.props.FloatProperty(default = valueList[2] , precision = dcc.FLOAT_PRECISION ),
                paramName+"_3": bpy.props.FloatProperty(default = valueList[3] , precision = dcc.FLOAT_PRECISION ),
                "templatedParameterTemplateMenu_" + parameterTemplateId + "_" + paramName: bpy.props.EnumProperty(items = rootTemplates, update = templateForParameterSelectedCallback(parameterTemplateId, rootSubTemplateId, paramName))
            })
        for textureName, value in parameterTemplate["textures"].items():
            # Only show textures that share a group with the variation.
            texture_group = shaderData["textures_group"][textureName]
            if texture_group not in variation_groups:
                continue

            dynamicGUIDict.update({
                    textureName+"Bool": bpy.props.BoolProperty(name=textureName, default=False),
                    textureName: bpy.props.StringProperty(default=value)
                    })
        clssName = 'I3D_UITemplateParameters_'+parameterTemplateId
        templateParameterClss = type(clssName, (bpy.types.PropertyGroup,), {'__annotations__': dynamicGUIDict})
        bpy.utils.register_class(templateParameterClss)
        
        try:
            setattr(bpy.types.Scene, clssName, bpy.props.PointerProperty(type=templateParameterClss))
        except Exception as e:
            print("Could not add class {} to scene".format(clssName))
            print(e)
            continue
        else:
            g_dynamicGUIClsDict[parameterTemplateId] = templateParameterClss

def shaderEnumUpdate(self,context):
    """ Creates and registers dynamic classes for dynamic GUI elements """

    global g_dynamicGUIClsDict
    if bpy.context.scene.get( 'I3D_UIShaderParameters' ):
        del bpy.context.scene[ 'I3D_UIShaderParameters' ]
    try:
        del bpy.types.Scene.I3D_UIShaderParameters
    except:
        pass
    if bpy.context.scene.get( 'I3D_UIShaderTextures' ):
        del bpy.context.scene[ 'I3D_UIShaderTextures' ]
    try:
        del bpy.types.Scene.I3D_UIShaderTextures
    except:
        pass
    for dynamicClass in g_dynamicGUIClsDict.values():
        bpy.utils.unregister_class(dynamicClass)
    g_dynamicGUIClsDict = {}

    shaderData = extractXMLShaderData()
    if shaderData:
        updateDynamicUIClassesForShaderParameters(shaderData, ["base"])
    else:
        print("No shader to load")

def shaderVariationEnumUpdate(self,context):
    """ Creates and registers dynamic classes for dynamic GUI elements """

    global g_dynamicGUIClsDict
    if bpy.context.scene.get( 'I3D_UIShaderParameters' ):
        del bpy.context.scene[ 'I3D_UIShaderParameters' ]
    try:
        del bpy.types.Scene.I3D_UIShaderParameters
    except:
        pass
    if bpy.context.scene.get( 'I3D_UIShaderTextures' ):
        del bpy.context.scene[ 'I3D_UIShaderTextures' ]
    try:
        del bpy.types.Scene.I3D_UIShaderTextures
    except:
        pass
    for dynamicClass in g_dynamicGUIClsDict.values():
        bpy.utils.unregister_class(dynamicClass)
    g_dynamicGUIClsDict = {}

    # check if data is overridden
    try:
        actObjName = context.active_object.name
    except:
        try:
            actObjName = dccBlender.getSelectedNodes()[0]
        except:
            actObjName = None
    materialObj = None
    if actObjName is not None:
        activeObject = bpy.data.objects[actObjName]
        materialObj = activeObject.active_material

    shaderData = extractXMLShaderData()
    if shaderData:
        variation_groups = ["base"]
        selected_variation = context.scene.I3D_UIexportSettings.I3D_shaderVariationEnum
        variation_groups_str = None
        if selected_variation in shaderData["variations_groups"]:
            variation_groups_str = shaderData["variations_groups"][selected_variation]
        if variation_groups_str is not None:
            variation_groups = variation_groups_str.split()

        updateDynamicUIClassesForShaderParameters(shaderData, variation_groups)
    else:
        print("No shader to load")


class I3D_OT_SelectionToOrigin(bpy.types.Operator):
    """Sets the origin position to the center of the selected vertices/edges/faces"""
    bl_idname = "i3d.selectiontoorigin"
    bl_label = "SelectionToOrigin"
    CONTEXT_MENU_ICON = "OBJECT_ORIGIN"

    def execute(self, context):
        if context.space_data.type == 'VIEW_3D':
            bpy.ops.object.mode_set(mode='OBJECT')

            avgPosition = Vector()
            numVertices = 0

            for vertex in bpy.context.object.data.vertices:
                if vertex.select:
                    worldPosition = bpy.context.object.matrix_world @ vertex.co
                    avgPosition += worldPosition
                    numVertices = numVertices + 1

            if numVertices > 0:
                pos = avgPosition / numVertices

                cursor_location = bpy.context.scene.cursor.location.xyz

                bpy.context.scene.cursor.location.xyz = pos
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

                bpy.context.scene.cursor.location.xyz = cursor_location
            else:
                self.report({'WARNING'}, "Nothing selected!")
                return {'CANCELLED'}

            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

    def getShowInContextMenu(context):
        if context.space_data.type == 'VIEW_3D':
            if context.object is not None:
                bm = bmesh.from_edit_mesh(context.object.data)
                for vert in bm.verts:
                    if vert.select:
                        return True

        return False


class I3D_OT_FaceNormalToOrigin(bpy.types.Operator):
    """Sets the origin rotation to equal the orientation of the selected face"""
    bl_idname = "i3d.facenormaltoorigin"
    bl_label = "FaceNormalToOrigin"
    CONTEXT_MENU_ICON = "ORIENTATION_NORMAL"

    def execute(self, context):
        if context.space_data.type == 'VIEW_3D':
            if context.object is None:
                self.report({'WARNING'}, "No face selected!")
                return {'CANCELLED'}

            mode = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode='OBJECT')

            object = context.object
            bm = bmesh.new()
            bm.from_mesh(object.data)

            bm.transform(object.matrix_world)
            bm.normal_update()
            face = bm.select_history.active

            if face is None:
                bpy.ops.object.mode_set(mode=mode)
                self.report({'WARNING'}, "No face selected!")
                return {'CANCELLED'}

            if not isinstance(face, bmesh.types.BMFace):
                bpy.ops.object.mode_set(mode=mode)
                self.report({'WARNING'}, "Function 'FaceNormalToOrigin' does only work with faces!")
                return {'CANCELLED'}

            tangent = face.calc_tangent_edge_pair().normalized()
            bt = face.normal.cross(tangent).normalized()

            worldMatrix = Matrix([tangent, bt, face.normal]).transposed().to_4x4()
            worldMatrix.translation = object.matrix_world.translation

            R = worldMatrix.to_3x3().normalized().to_4x4()

            worldMatrix = object.matrix_world
            location = worldMatrix.to_3x3().normalized().to_4x4().inverted() @ R
            object.matrix_world = (Matrix.Translation(worldMatrix.translation) @ R @ Matrix.Diagonal(worldMatrix.to_scale()).to_4x4())
            object.data.transform(location.inverted())

            bpy.ops.object.mode_set(mode=mode)

            bm.free()

            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

    def getShowInContextMenu(context):
        if context.space_data.type == 'VIEW_3D':
            if context.object is not None:
                bm = bmesh.from_edit_mesh(context.object.data)
                for face in bm.faces:
                    if face.select:
                        return True
        return False


class I3D_OT_FreezeTranslation(bpy.types.Operator):
    """Equals the origin translation with the translation of the parent object"""
    bl_idname = "i3d.freezetranslation"
    bl_label = "FreezeTranslation"
    CONTEXT_MENU_ICON = "CON_LOCLIMIT"

    def execute(self, context):
        if context.space_data.type == 'VIEW_3D':
            bpy.ops.object.mode_set(mode='OBJECT')

            object = context.object
            loc = (0, 0, 0)
            if object.parent is not None:
                loc = object.parent.location.xyz

            if object.type == "MESH":
                cursor_location = bpy.context.scene.cursor.location.xyz

                bpy.context.scene.cursor.location.xyz = loc
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

                bpy.context.scene.cursor.location.xyz = cursor_location
            elif object.type == "ARMATURE":
                loc = (0, 0, 0)
                if object.parent is not None:
                    loc = object.parent.location.xyz

                object.location.xyz = loc
                for bone in object.pose.bones:
                    bone.location.xyz = (0, 0, 0)
            else:
                self.report({'WARNING'}, "'FreezeTranslation' not supported for '%s'" % object.type)

            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

    def getShowInContextMenu(context):
        if context.space_data.type == 'VIEW_3D':
            if context.mode == "OBJECT":
                if len(bpy.context.selected_objects) > 0:
                    return True

        return False


class I3D_OT_FreezeRotation(bpy.types.Operator):
    """Equals the origin rotation with the rotation of the parent object"""
    bl_idname = "i3d.freezerotation"
    bl_label = "FreezeRotation"
    CONTEXT_MENU_ICON = "CON_ROTLIMIT"

    def execute(self, context):
        if context.space_data.type == 'VIEW_3D':
            bpy.ops.object.mode_set(mode='OBJECT')

            if len(bpy.context.selected_objects) == 0:
                self.report({'WARNING'}, "No object(s) selected!")
                return {'CANCELLED'}

            for object in bpy.context.selected_objects:
                listOfChildren = []
                for child in object.children:
                    listOfChildren += [child]
                    bpy.ops.object.select_all(action='DESELECT')
                    child.select_set(True)
                    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

                worldMatrix = None
                if object.parent is None:
                    worldMatrix = Euler((0, 0, 0)).to_matrix()
                else:
                    worldMatrix = object.parent.matrix_world

                R = worldMatrix.to_3x3().normalized().to_4x4()

                worldMatrix = object.matrix_world
                location = worldMatrix.to_3x3().normalized().to_4x4().inverted() @ R
                object.matrix_world = (Matrix.Translation(worldMatrix.translation) @ R @ Matrix.Diagonal(worldMatrix.to_scale()).to_4x4())
                if hasattr(object.data, "transform"):
                    object.data.transform(location.inverted())

                # set parent back again
                for child in listOfChildren:
                    bpy.data.scenes['Scene'].tool_settings.use_transform_data_origin = False
                    child.parent = object
                    child.matrix_parent_inverse = object.matrix_world.inverted()
                    bpy.data.scenes['Scene'].tool_settings.use_transform_data_origin = True
                    child.select_set(False)

                object.select_set(True)

            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

    def getShowInContextMenu(context):
        if context.space_data.type == 'VIEW_3D':
            if context.mode == "OBJECT":
                if len(bpy.context.selected_objects) > 0:
                    return True

        return False


class I3D_OT_CreateEmpty(bpy.types.Operator):
    """Creates empty group at selected vertex position or as child of selected object(s) or at root level if nothing selected"""
    bl_idname = "i3d.createempty"
    bl_label = "CreateEmpty"
    CONTEXT_MENU_ICON = "OUTLINER_OB_EMPTY"

    def execute(self, context):
        def createEmpty(parent, pos):
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=pos, radius=0.25)
            empty = bpy.context.view_layer.objects.active

            if parent is not None:
                empty.matrix_world = parent.matrix_world
                empty.location.xyz = pos
                empty.parent = parent
                empty.matrix_parent_inverse = empty.matrix_world.inverted()

                if "Punch" in parent.name:
                    empty.name = parent.name.replace("Punch", "Ref")
                else:
                    empty.name = parent.name + "_Empty"
            else:
                empty.name = "EmptyGroup"

        if context.space_data.type == 'VIEW_3D':
            if bpy.context.active_object is not None:
                mode = bpy.context.active_object.mode
                if mode == "EDIT":
                    bpy.ops.object.mode_set(mode='OBJECT')

                    avgPosition = Vector()
                    numVertices = 0

                    for vertex in bpy.context.object.data.vertices:
                        if vertex.select:
                            worldPosition = bpy.context.object.matrix_world @ vertex.co
                            avgPosition += worldPosition
                            numVertices = numVertices + 1

                    if numVertices > 0:
                        pos = avgPosition / numVertices
                        createEmpty(bpy.context.object, pos)
                    else:
                        self.report({'WARNING'}, "No vertices selected to create empty at. Switch to object mode or select vertices!")
                        return {'CANCELLED'}

                elif mode == "OBJECT":
                    for object in bpy.context.selected_objects:
                        createEmpty(object, object.location.xyz)

                    if len(bpy.context.selected_objects) == 0:
                        createEmpty(None, (0, 0, 0))
            else:
                if len(bpy.context.selected_objects) == 0:
                    createEmpty(None, (0, 0, 0))

            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

    def getShowInContextMenu(context):
        if context.space_data.type == 'VIEW_3D':
            if context.mode == "OBJECT":
                return True
            else:
                if context.object is not None:
                    bm = bmesh.from_edit_mesh(context.object.data)
                    for vert in bm.verts:
                        if vert.select:
                            return True

        return False


class I3D_OT_AlignYAxis(bpy.types.Operator):
    """Rotate origin towards other objects origin"""
    bl_idname = "i3d.alignyaxis"
    bl_label = "AlignYAxis"
    CONTEXT_MENU_ICON = "ORIENTATION_GLOBAL"

    def execute(self, context):

        if context.space_data.type == 'VIEW_3D':
            if len(bpy.context.selected_objects) != 2:
                self.report({"WARNING"}, "Select exactly 2 objects to align")
                return {'FINISHED'}

            targetObject = bpy.context.active_object

            sourceObject = targetObject
            if bpy.context.selected_objects[0] == targetObject:
                sourceObject = bpy.context.selected_objects[1]
            else:
                sourceObject = bpy.context.selected_objects[0]

            listOfChildren = []
            for child in sourceObject.children:
                listOfChildren += [child]
                bpy.ops.object.select_all(action='DESELECT')
                child.select_set(True)
                bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

            obj1_trans = Vector((sourceObject.matrix_world.translation[0], sourceObject.matrix_world.translation[1], sourceObject.matrix_world.translation[2]))
            obj2_trans = Vector((targetObject.matrix_world.translation[0], targetObject.matrix_world.translation[1], targetObject.matrix_world.translation[2]))

            t = (obj1_trans - obj2_trans).normalized()

            tangent = t.cross(Vector((0, 0, 1))).normalized()
            bt = t.cross(tangent).normalized()

            targetMatrix = (Matrix([tangent, bt, t]).transposed() @ Euler((math.pi * 0.5, 0, 0)).to_matrix()).to_4x4()
            targetMatrix.translation = sourceObject.matrix_world.translation

            R = targetMatrix.to_3x3().normalized().to_4x4()

            worldMatrix = sourceObject.matrix_world
            location = worldMatrix.to_3x3().normalized().to_4x4().inverted() @ R
            sourceObject.matrix_world = (Matrix.Translation(worldMatrix.translation) @ R @ Matrix.Diagonal(worldMatrix.to_scale()).to_4x4())
            sourceObject.data.transform(location.inverted())

            if targetObject in listOfChildren:
                targetMatrix.translation = targetObject.matrix_world.translation

                R = targetMatrix.to_3x3().normalized().to_4x4()

                worldMatrix = targetObject.matrix_world
                location = worldMatrix.to_3x3().normalized().to_4x4().inverted() @ R
                targetObject.matrix_world = (Matrix.Translation(worldMatrix.translation) @ R @ Matrix.Diagonal(worldMatrix.to_scale()).to_4x4())
                targetObject.data.transform(location.inverted())

            # set parent back again
            for child in listOfChildren:
                bpy.data.scenes['Scene'].tool_settings.use_transform_data_origin = False
                child.parent = sourceObject
                child.matrix_parent_inverse = sourceObject.matrix_world.inverted()
                bpy.data.scenes['Scene'].tool_settings.use_transform_data_origin = True

            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

    def getShowInContextMenu(context):
        if context.space_data.type == 'VIEW_3D':
            if context.mode == "OBJECT":
                if len(bpy.context.selected_objects) == 2:
                    return True

        return False


class I3D_OT_MenuExport( bpy.types.Operator ):
    """
    Button to open the GIANTS I3D Exporter
    """

    bl_label = "I3D Exporter"
    bl_idname = "i3d.menuexport"

    def execute( self, context ):
        try:    #prevent double registration
            for cls in classes:
                bpy.utils.register_class(cls)
        except:
            pass
        return {'FINISHED'}
    
class I3D_PT_PanelExport( bpy.types.Panel ):
    """ GUI Panel for the GIANTS I3D Exporter visible in the 3D Viewport """

    bl_idname       = "I3D_PT_PanelExport"
    bl_label        = "PMR GIANTS I3D Exporter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PMR GIANTS I3D Exporter"


    def __init__(self):
        global g_modalsRunning
        self.filepath      = bpy.path.abspath(bpy.context.scene.I3D_UIexportSettings.I3D_exportFileLocation)
        if not g_modalsRunning:
            bpy.ops.i3d.active_object('INVOKE_DEFAULT')
            bpy.ops.i3d.predef_check('INVOKE_DEFAULT')
            g_modalsRunning = True

    def draw( self, context ):

        layout = self.layout
        box = layout.box()
        row = box.row()
        split = row.split(factor=0.35)
        row = split.row()
        row.alignment = "LEFT"
        row.label(text="IndexPath:")
        row.label(text=dcc.I3DgetNodeIndex(context.scene.I3D_UIexportSettings.UI_ActiveObjectName))
        row = split.row()
        row.alignment = "LEFT"
        row.label(text="Node Name:")
        row.label(text=context.scene.I3D_UIexportSettings.UI_ActiveObjectName)
        split = box.split(factor = 0.04)
        split.prop(context.scene.I3D_UIexportSettings, "I3D_XMLConfigExport")
        row = split.row()
        row.enabled = context.scene.I3D_UIexportSettings.I3D_XMLConfigExport
        row.prop(context.scene.I3D_UIexportSettings, "I3D_XMLConfigIdentification")
        row.operator("i3d.panelxmlidentification_buttonadd",text="Use Node Name")

        layout.prop( context.scene.I3D_UIexportSettings,  "UI_settingsMode", expand = True )
        #-----------------------------------------
        # "Export" tab
        if   'exp'  == context.scene.I3D_UIexportSettings.UI_settingsMode:
            #-----------------------------------------
            # "Export Options" box
            box = layout.box()
            row = box.row()
            # expand button for "Export Options"
            row.prop(   context.scene.I3D_UIexportSettings,
                        "UI_exportOptions",
                        text = "Export Options",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_exportOptions else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )
            # expanded view
            if context.scene.I3D_UIexportSettings.UI_exportOptions:
                row = box.row()
                split = row.split(factor=0.4)
                col = split.column()
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_exportAnimation" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_exportShapes"    )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_exportLights"      )
                split = split.split(factor = 0.16)
                col = split.column()
                split = split.split(factor = 0.8)
                col = split.column()
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_exportUserAttributes"  )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_exportNurbsCurves" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_binaryFiles"     )

            # -----------------------------------------
            # "Shape Export Subparts" box
            box = layout.box()
            row = box.row()
            # expand button for "Shape Export Subparts"
            row.prop(   context.scene.I3D_UIexportSettings,
                        "UI_shapeExportSubparts",
                        text = "Shape Export Subparts",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_shapeExportSubparts else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )
            if context.scene.I3D_UIexportSettings.UI_shapeExportSubparts:
                row.label(text="defaults mesh exports:if there is a shapefile these are ignored")
                row = box.row()
                split = row.split(factor=0.4)
                col = split.column()
                col.prop( context.scene.I3D_UIexportSettings, "I3D_export32bitposition"     )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_exportNormals"     )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_use32bitQT"     )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_exportTangents"     )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_exportTangentsBinaryRecalc"     )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_exportColors"      )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_exportMergeGroups")
                split = split.split(factor = 0.16)
                col = split.column()
                split = split.split(factor = 0.8)
                col = split.column()
                col.prop( context.scene.I3D_UIexportSettings, "I3D_exportTexCoords"   )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_exportTexCoordsUVDensity"   )
 
                col.prop( context.scene.I3D_UIexportSettings, "I3D_exportSkinWeigths" )

                if not context.scene.I3D_UIexportSettings.I3D_exportMergeGroups :
                    col.prop( context.scene.I3D_UIexportSettings, "I3D_UImaxMeshSizeX"  )
                    col.prop( context.scene.I3D_UIexportSettings, "I3D_UImaxMeshSizeY"  )
                    col.prop( context.scene.I3D_UIexportSettings, "I3D_UImaxMeshSizeZ"  )

             # -----------------------------------------
            # -----------------------------------------
            # "Miscellaneous" box
            box = layout.box()
            row = box.row()
            # expand button for "Miscellaneous"
            row.prop(   context.scene.I3D_UIexportSettings,
                        "UI_miscellaneous",
                        text = "Miscellaneous",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_miscellaneous else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )
            if context.scene.I3D_UIexportSettings.UI_miscellaneous:
                row = box.row()
                split = row.split(factor=0.4)
                col = split.column()
                col.prop( context.scene.I3D_UIexportSettings, "I3D_exportVerbose"       )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_exportApplyModifiers"  )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_generateexporterprofile"  )
                split = split.split(factor = 0.16)
                col = split.column()
                split = split.split(factor = 0.8)
                col = split.column()
                col.prop( context.scene.I3D_UIexportSettings, "I3D_UIexportCopyFiles" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_exportRelativePaths" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_exportGameRelativePath" )
                split = box.split()
                split.prop( context.scene.I3D_UIexportSettings, "I3D_exportAxisOrientations"  )
            # -----------------------------------------
            # "Game Location" box
            box = layout.box()
            row = box.row()
            # expand button for "Miscellaneous"
            row.prop(   context.scene.I3D_UIexportSettings,
                        "UI_gameLocation",
                        text = "Game Location",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_gameLocation else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )
            if context.scene.I3D_UIexportSettings.UI_gameLocation:

                row = box.row()
                # row.enabled = context.scene.I3D_UIexportSettings.I3D_exportGameRelativePath
                # row.prop( context.scene.I3D_UIexportSettings, "I3D_gameLocation"  )
                row.prop( context.scene.I3D_UIexportSettings, "I3D_gameLocationDisplay"  )

                row.operator( "i3d.openfolderfilebrowser", icon='FILEBROWSER',text="").state = 1
                if dirf.isWindows():
                    row.operator( "i3d.panelrefreshgamepath", icon='ZOOM_ALL',text="")
            # -----------------------------------------
            # "XML config File" box
            box = layout.box()
            row = box.row()
            row.prop(   context.scene.I3D_UIexportSettings,
                        "UI_xmlConfig",
                        text = "XML Config Files",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_xmlConfig else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )
            if context.scene.I3D_UIexportSettings.UI_xmlConfig:    #Tab
                xmlPaths = context.scene.I3D_UIexportSettings.I3D_updateXMLFilePath.split(";")
                for xmlPath in xmlPaths:
                    if xmlPath != "":
                        xmlPathRel = xmlPath
                        if bpy.data.filepath != "":
                            if os.path.isfile(bpy.data.filepath):
                                try:
                                    xmlPathRel = os.path.relpath(xmlPath, bpy.data.filepath).replace("..\\", "")
                                except ValueError:
                                    pass

                        row = box.row()
                        row.label(text=xmlPathRel)
                        row.operator("i3d.panelremovexmlpath_buttonremove", text="", icon='X').state = xmlPath

                row = box.row(align=True)
                row.alignment = 'RIGHT'
                row.label(text="Add XML Config File  ")
                row.operator("i3d.openxmlfilebrowser", text="", icon='PLUS')
            # -----------------------------------------
            # "Output File" box
            box = layout.box()
            row = box.row()
            # expand button for "Output File"
            row.prop(   context.scene.I3D_UIexportSettings,
                        "UI_outputFile",
                        text = "Output File",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_outputFile else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )
            if context.scene.I3D_UIexportSettings.UI_outputFile:    #Tab
                row = box.row()
                row.prop( context.scene.I3D_UIexportSettings, "I3D_exportUseSoftwareFileName" )
                row = box.row()
                row.enabled = not context.scene.I3D_UIexportSettings.I3D_exportUseSoftwareFileName
                row.prop( context.scene.I3D_UIexportSettings, "I3D_exportFileLocation" )
                row.operator("i3d.openi3dfilebrowser",icon = 'FILEBROWSER',text = "")
            #-----------------------------------------
            row = layout.row( align = True )
            row.enabled = os.path.isdir(context.scene.I3D_UIexportSettings.I3D_gameLocationDisplay)
            if row.enabled :
                if(bpy.context.scene.I3D_UIexportSettings.I3D_exportUseSoftwareFileName):
                    row.enabled =  not(bpy.data.filepath == "") 
                else:
                    row.enabled =  not(bpy.context.scene.I3D_UIexportSettings.I3D_exportFileLocation == "")  

            row.operator( "i3d.panelexport_buttonexport", text = "Export All"      ).state = 1
            row.operator( "i3d.panelexport_buttonexport", text = "Export Selected" ).state = 2
            row = layout.row()
            row.operator( "i3d.panelexport_buttonexport", text = "Update XML" ).state = 3
        #-----------------------------------------
        # "Attributes" tab
        elif 'attr' == context.scene.I3D_UIexportSettings.UI_settingsMode:
            #-----------------------------------------
            # "Current Node" box
            box = layout.box()
            row = box.row()
            # expand button for "Current Node"
            row.prop(   context.scene.I3D_UIexportSettings,
                        "UI_currentNode",
                        text = "Loaded Node",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_currentNode else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )
            # expanded view
            if context.scene.I3D_UIexportSettings.UI_currentNode:
                row = box.row()
                row.prop( context.scene.I3D_UIexportSettings, "UI_autoAssign", text = "Auto Assign")
                row = box.row()
                row.enabled = False
                row.prop( context.scene.I3D_UIexportSettings, "I3D_nodeName", text = "Loaded Node" )
                row = box.row()
                row.enabled = False
                row.prop( context.scene.I3D_UIexportSettings, "I3D_nodeIndex", text = "Node Index" )
                row = box.row()
                row.prop( context.scene.I3D_UIexportSettings, "I3D_lockedGroup", text = "Locked Group" )
            #-----------------------------------------
            # "Predefined Body" box
            box = layout.box()
            row = box.row()
            row.prop(   context.scene.I3D_UIexportSettings,
                        "UI_predefined",
                        text = "Predefined",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_predefined else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )
            if context.scene.I3D_UIexportSettings.UI_predefined:
                row = box.row()
                row.prop(context.scene.I3D_UIexportSettings,"I3D_predefinedPhysic")
                row = box.row()
                row.prop(context.scene.I3D_UIexportSettings,"I3D_predefinedNonPhysic")
                row = box.row()
                row.label(text = "Current Preset:")
                row.label(text = context.scene.I3D_UIexportSettings.I3D_selectedPredefined + ("*" if context.scene.I3D_UIexportSettings.I3D_predefHasChanged  else ""))
            #-----------------------------------------
            # "Rigid Body" box
            box = layout.box()
            row = box.row()
            # expand button for "Rigid Body"
            row.prop(   context.scene.I3D_UIexportSettings,
                        "UI_rigidBody",
                        text = "Rigid Body",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_rigidBody else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False)
            # expanded view
            if context.scene.I3D_UIexportSettings.UI_rigidBody:
                col = box.column()
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_static",                text = "Static" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_kinematic",             text = "Kinematic" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_dynamic",               text = "Dynamic" )
                subcol = col.column()
                subcol.enabled = not context.scene.I3D_UIexportSettings.I3D_compoundChild
                subcol.prop( context.scene.I3D_UIexportSettings,  "I3D_compound",              text = "Compound" )
                subcol2 = col.column()
                subcol2.enabled = not context.scene.I3D_UIexportSettings.I3D_compound
                subcol2.prop( context.scene.I3D_UIexportSettings,  "I3D_compoundChild",         text = "Compound Child" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_collision",             text = "Collision" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_collisionFilterPreset", text = "Collision Preset" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_restitution",           text = "Restitution" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_staticFriction",        text = "Static Friction" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_dynamicFriction",       text = "Dynamic Friction" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_linearDamping",         text = "Linear Damping" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_angularDamping",        text = "Angular Damping" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_density",               text = "Density" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_solverIterationCount",  text = "Solver Iterations" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_ccd",                   text = "Continues Collision Detection" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_trigger",               text = "Trigger" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_splitType",             text = "Split Type" )
                row = col.row()
                row.prop( context.scene.I3D_UIexportSettings,  "I3D_splitMinU",             text = "Split Min U" )
                row.prop( context.scene.I3D_UIexportSettings,  "I3D_splitMaxU",             text = "Split Max U" )
                row = box.row()
                row.prop( context.scene.I3D_UIexportSettings,  "I3D_splitMinV",             text = "Split Min V" )
                row.prop( context.scene.I3D_UIexportSettings,  "I3D_splitMaxV",             text = "Split Max V" )
                row = box.row()
                row.prop( context.scene.I3D_UIexportSettings,  "I3D_splitUvWorldScale",     text = "Split UV's worldScale" )
            #-----------------------------------------
            # "Joint" box
            box = layout.box()
            row = box.row()
            # expand button for "Joint"
            row.prop(   context.scene.I3D_UIexportSettings,
                        "UI_joint",
                        text = "Joint",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_joint else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )
            # expanded view
            if context.scene.I3D_UIexportSettings.UI_joint:
                col = box.column()
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_joint",            text = "Joint" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_projection",       text = "Projection" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_projDistance",     text = "Projection Distance" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_projAngle",        text = "Projection Angle" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_xAxisDrive",       text = "X-Axis Drive" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_yAxisDrive",       text = "Y-Axis Drive" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_zAxisDrive",       text = "Z-Axis Drive" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_drivePos",         text = "Drive Position" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_driveForceLimit",  text = "Drive Force Limit" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_driveSpring",      text = "Drive Spring" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_driveDamping",     text = "Drive Damping" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_breakableJoint",   text = "Breakable" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_jointBreakForce",  text = "Break Force" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_jointBreakTorque", text = "Break Torque" )
            #-----------------------------------------
            # "Rendering" box
            box = layout.box()
            row = box.row()
            # expand button for "Rendering"
            row.prop(   context.scene.I3D_UIexportSettings,
                        "UI_rendering",
                        text = "Rendering",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_rendering else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )
            # expanded view
            if context.scene.I3D_UIexportSettings.UI_rendering:
                col = box.column()
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_oc",                    text = "Occluder" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_castsShadows",          text = "Cast Shadowmap" )                
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_receiveShadows",        text = "Receive Shadowmap" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_renderedInViewports",   text = "Rendered in Viewports" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_renderedInEnvmap",      text = "Rendered in envmap" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_grassMetaDataProvider", text = "Grass Metadata Provider" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_grassMesh",             text = "Grass Mesh" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_highdDetailMesh",       text = "High Detail Mesh" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_nonRenderable",         text = "Non Renderable" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_clipDistance",          text = "Clip Distance" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_objectMask",            text = "Object Mask" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_navMeshMask",           text = "Nav Mesh Mask" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_doubleSided",           text = "Double Sided" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_decalLayer",            text = "Decal Layer" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_mergeGroup",            text = "Merge Group" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_mergeGroupRoot",        text = "Merge Group Root" )

                split = col.split(factor=0.25)
                split.label(text="Bounding Volume")
                split.prop( context.scene.I3D_UIexportSettings,  "I3D_boundingVolume", text = "" )
                col2 = split.column()
                col2.prop(context.scene.I3D_UIexportSettings, "I3D_boundingVolumeMergeGroup")

                col = col.column()
                try:

                    if context.scene.I3D_UIexportSettings.I3D_nodeName in bpy.data.objects and bpy.data.objects[context.scene.I3D_UIexportSettings.I3D_nodeName].type == "EMPTY":
                        split = col.split(factor=0.3)
                        split.prop(  context.scene.I3D_UIexportSettings, "I3D_mergeChildren")

                        col2 = split.column()
                        # col2.enabled = context.scene.I3D_UIexportSettings.I3D_mergeChildren   #alternative option
                        if context.scene.I3D_UIexportSettings.I3D_mergeChildren:
                            col2.label(text="Freeze Attribute")
                            subSplit = col2.split()
                            col2.prop(context.scene.I3D_UIexportSettings,"I3D_mergeChildrenFreezeTranslation")
                            col2.prop(context.scene.I3D_UIexportSettings,"I3D_mergeChildrenFreezeRotation")
                            col2.prop(context.scene.I3D_UIexportSettings,"I3D_mergeChildrenFreezeScale")
                except Exception as e:
                    print(e)
                    pass

                col.prop( context.scene.I3D_UIexportSettings,  "I3D_terrainDecal",   text = "Terrain Decal" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_cpuMesh",        text = "CPU Mesh" )
                col.prop( context.scene.I3D_UIexportSettings,  "I3D_lod",            text = "LOD" )
                row = col.row()
                row.enabled = False
                row.prop( context.scene.I3D_UIexportSettings, "I3D_lod0", text = "Child 0 Distance" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_lod1", text = "Child 1 Distance" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_lod2", text = "Child 2 Distance" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_lod3", text = "Child 3 Distance" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_lodBlending", text = "Lod Blending" )
                row = box.row()
                row.prop( context.scene.I3D_UIexportSettings, "I3D_vertexCompressionRange")
            #-----------------------------------------
            # "Environment" box
            box = layout.box()
            row = box.row()
            row.prop( context.scene.I3D_UIexportSettings,
                        "UI_environment",
                        text = "Visibility Conditions",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_environment else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )
            if context.scene.I3D_UIexportSettings.UI_environment:
                col = box.column()
                col.prop( context.scene.I3D_UIexportSettings, "I3D_minuteOfDayStart", text = "Minute Of Day Start" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_minuteOfDayEnd", text = "Minute Of Day End" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_dayOfYearStart", text = "Day Of Year Start" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_dayOfYearEnd", text = "Day Of Year End" )
                box = col.box()
                row = box.row()
                row.prop( context.scene.I3D_UIexportSettings, "I3D_weatherMask", text = "Weather Mask (Dec)" )
                row.operator('i3d.bitmaskeditor', icon='THREE_DOTS',text='').state = 0
                row = box.row()
                row.prop( context.scene.I3D_UIexportSettings, "I3D_weatherPreventMask", text = "Weather Prevent Mask (Dec)" )
                row.operator('i3d.bitmaskeditor',  icon='THREE_DOTS',text='').state = 1
                row = box.row()
                row.prop( context.scene.I3D_UIexportSettings, "I3D_viewerSpacialityMask", text = "Viewer Spaciality Mask (Dec)" )
                row.operator('i3d.bitmaskeditor',  icon='THREE_DOTS',text='').state = 2
                row = box.row()
                row.prop( context.scene.I3D_UIexportSettings, "I3D_viewerSpacialityPreventMask", text = "Viewer Spaciality Prevent Mask (Dec)" )
                row.operator('i3d.bitmaskeditor',  icon='THREE_DOTS',text='').state = 3
                col.prop( context.scene.I3D_UIexportSettings, "I3D_renderInvisible", text = "Render Invisible")
                col.prop( context.scene.I3D_UIexportSettings, "I3D_visibleShaderParam", text = "Visible Shader Param" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_forceVisibilityCondition", text = "Force Visibility Condition" )

            #-----------------------------------------
            # "Object Data Texture" box
            box = layout.box()
            row = box.row()
            row.prop( context.scene.I3D_UIexportSettings,
                        "UI_objectDataTexture",
                        text = "Object Data Texture",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_objectDataTexture else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )
            if context.scene.I3D_UIexportSettings.UI_objectDataTexture:
                col = box.column()
                col.prop( context.scene.I3D_UIexportSettings, "I3D_objectDataFilePath", text = "File Path" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_objectDataHierarchicalSetup", text = "Hierarchical Setup" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_objectDataHideFirstAndLastObject", text = "HideFirst And Last" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_objectDataExportPosition", text = "Export Position" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_objectDataExportOrientation", text = "Export Orientation" )
                col.prop( context.scene.I3D_UIexportSettings, "I3D_objectDataExportScale", text = "Export Scale" )

            #-----------------------------------------
            # "Light" attributes box
            if context.scene.I3D_UIexportSettings.UI_showLightAttributes:
                box = layout.box()
                row = box.row()
                row.prop( context.scene.I3D_UIexportSettings,
                            "UI_lightAttributes",
                            text = "Light",
                            icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_lightAttributes else 'TRIA_RIGHT',
                            icon_only = False,
                            emboss = False )
                if context.scene.I3D_UIexportSettings.UI_lightAttributes:
                    col = box.column()
                    col.prop( context.scene.I3D_UIexportSettings, "UI_lightUseShadow")
                    enableShadowSettings = False
                    if context.scene.I3D_UIexportSettings.UI_lightUseShadow:
                        enableShadowSettings = True
                    propRow = col.row()
                    propRow.prop( context.scene.I3D_UIexportSettings, "I3D_softShadowsLightSize")
                    propRow.enabled = enableShadowSettings
                    propRow = col.row()
                    propRow.prop( context.scene.I3D_UIexportSettings, "I3D_softShadowsLightDistance")
                    propRow.enabled = enableShadowSettings
                    propRow = col.row()
                    propRow.prop( context.scene.I3D_UIexportSettings, "I3D_softShadowsDepthBiasFactor")
                    propRow.enabled = enableShadowSettings
                    propRow = col.row()
                    propRow.prop( context.scene.I3D_UIexportSettings, "I3D_softShadowsMaxPenumbraSize")
                    propRow.enabled = enableShadowSettings

                    iesProfileFileRow = col.row()
                    iesProfileFileRow.prop( context.scene.I3D_UIexportSettings, "I3D_iesProfileFile", text = "IES Profile File")
                    iesProfileFileRow.operator("i3d.openiesfilebrowser", icon = 'FILEBROWSER', text = "")
            
            #-----------------------------------------
            row = layout.row( align = True )
            # row.enabled = not context.scene.I3D_UIexportSettings.UI_autoAssign
            col = row.column()
            col.enabled = not context.scene.I3D_UIexportSettings.UI_autoAssign
            col.operator( "i3d.panelexport_buttonattr", text = "Load Current"    ).state = 1
            col = row.column()
            col.enabled = not context.scene.I3D_UIexportSettings.UI_autoAssign
            col.operator( "i3d.panelexport_buttonattr", text = "Save Current"    ).state = 2
            col = row.column()
            # col.enabled = not context.scene.I3D_UIexportSettings.UI_autoAssign
            col.operator( "i3d.panelexport_buttonattr", text = "Remove Current"  ).state = 3
            row = layout.row( align = True )
            row.enabled = not context.scene.I3D_UIexportSettings.UI_autoAssign

            col = row.column()
            # col.enabled = not context.scene.I3D_UIexportSettings.UI_autoAssign
            col.operator( "i3d.panelexport_buttonattr", text = "Apply Selected"  ).state = 4
            col = row.column()
            col.operator( "i3d.panelexport_buttonattr", text = "Remove Selected" ).state = 5
        #-----------------------------------------
        # "newmaterial" tab
        #-----------------------------------------
        elif 'newMaterial' == context.scene.I3D_UIexportSettings.UI_settingsMode: 
            if gS4MaterialPanel != None:
                gS4MaterialPanel.draw(context,layout)
       #-----------------------------------------
        # "shapeAttribute" tab
        #-----------------------------------------
        elif 'shapeAttribute' == context.scene.I3D_UIexportSettings.UI_settingsMode: 
            if gS4ShapePanel != None:
                gS4ShapePanel.draw(context,layout)

        #-----------------------------------------
        # "Shader" tab
        #-----------------------------------------
        elif 'shader' == context.scene.I3D_UIexportSettings.UI_settingsMode:
            # Custom shader folder.
            box = layout.box()
            row = box.row()
            row.prop(   context.scene.I3D_UIexportSettings,
                        "UI_shaderFolder",
                        text = "Shaders Folder",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_shaderFolder else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )

            if context.scene.I3D_UIexportSettings.UI_shaderFolder:
                split = box.split(factor = 0.8)
                split.prop(context.scene.I3D_UIexportSettings, "I3D_shaderFolderLocation")
                row = split.row()
                row.operator("i3d.openfolderfilebrowser", icon='FILEBROWSER',text = "").state = 2

                if dirf.isWindows():

                    row.operator("i3d.panelsetgameshader", icon='ZOOM_ALL')

            # Selected material dropdown.
            box = layout.box()
            row = box.row()
            split = row.split(factor = 0.8)
            row = split.row()
            row.prop(context.scene.I3D_UIexportSettings, "I3D_selectedMaterialEnum")
            row = split.row()
            row.operator("i3d.openmaterialtemplateswindow")
            
            # Shader and variation dropdowns.
            box = layout.box()
            row = box.row()
            row.prop(context.scene.I3D_UIexportSettings,"I3D_shaderEnum")
            row = box.row()
            row.prop(context.scene.I3D_UIexportSettings,"I3D_shaderVariationEnum")

            # Custom parameters and textures.
            box = layout.box()
            row = box.row()
            row.label(text="Parameters")

            global g_dynamicGUIClsDict
            if "parameters" in g_dynamicGUIClsDict:
                enableText = False
                for k,i in g_dynamicGUIClsDict["parameters"].__annotations__.items():
                    if k.endswith("Bool"):
                        row = box.row()
                        row.prop(context.scene.I3D_UIShaderParameters,k,text="")
                        if (getattr(context.scene.I3D_UIShaderParameters, k)):
                            enableText = True
                        else:
                            enableText = False
                    else:
                        if(k.endswith("_0")):
                            row.label(text=k.strip("_0"))
                        row_items = row.row()
                        row_items.enabled = enableText
                        row_items.prop(context.scene.I3D_UIShaderParameters,k,text= "")

            box = layout.box()
            row = box.row()
            row.label(text="Textures")
            if "textures" in g_dynamicGUIClsDict:
                enableText = False
                for k,i in g_dynamicGUIClsDict["textures"].__annotations__.items():
                    if k.endswith("Bool"):
                        row = box.row()
                        row.prop(context.scene.I3D_UIShaderTextures,k,text="")
                        if (getattr(context.scene.I3D_UIShaderTextures, k)):
                            enableText = True
                        else:
                            enableText = False
                    else:
                        row_items = row.row()
                        row_items.enabled = enableText
                        row_items.prop(context.scene.I3D_UIShaderTextures,k)

            for dynamicGUIClsName, dynamicGUICls in g_dynamicGUIClsDict.items():
                if dynamicGUIClsName == "textures" or dynamicGUIClsName == "parameters":
                    continue
                # Otherwise we assume that its a template parameter
                clssName = 'I3D_UITemplateParameters_'+dynamicGUIClsName

                box = layout.box()
                row = box.row()
                row.label(text=dynamicGUIClsName) # TODO(jdellsperger): brandColor instead of Brand Color...

                try:
                    dataClass = getattr(context.scene, clssName)
                except Exception as e:
                    print("Could not add class {} to scene".format(clssName))
                    print(e)
                    continue
                else:
                    enableText = False
                    for k,i in dynamicGUICls.__annotations__.items():
                        if k.endswith("Bool"):
                            row = box.row()
                            row.prop(dataClass, k,text="")
                            if (getattr(dataClass, k)):
                                enableText = True
                            else:
                                enableText = False
                        else:
                            if k.endswith("_0"):
                                split = row.split(factor=0.195)
                                c = split.column()
                                c.label(text=k[:-2])
                                row = split.split()
                            elif not k.endswith("_1") and not k.endswith("_2") and not k.endswith("_3") and not k.startswith("templatedParameterTemplateMenu_"):
                                if "name" in i.keywords:
                                    # This is a template dropdown
                                    split = row.split(factor=0.195)
                                    c = split.column()
                                    c.label(text=i.keywords["name"])
                                    row = split.split()
                                else:
                                    split = row.split(factor=0.195)
                                    c = split.column()
                                    c.label(text=k)
                                    row = split.split()
                            row_items = row.row()
                            row_items.enabled = enableText
                            row_items.prop(dataClass, k, text = "")

            box = layout.box()
            row = box.row()
            row.prop(context.scene.I3D_UIexportSettings,'I3D_shadingRate')
            row = box.row()
            split = row.split(factor = 0.7)
            row = split.row()
            row.prop(context.scene.I3D_UIexportSettings, "I3D_materialSlotName")
            row = split.row()
            row.operator("i3d.usematerialnameasslotname")
            row = box.row()
            row.prop(context.scene.I3D_UIexportSettings,'I3D_alphaBlending')

            box = layout.box()
            row = box.row()
            row.prop(   context.scene.I3D_UIexportSettings,
                        "UI_materialTools",
                        text = "Tools",
                        icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_materialTools else 'TRIA_RIGHT',
                        icon_only = False,
                        emboss = False )

            row = layout.row()
            row.operator( "i3d.paneladdshader_buttonadd")
            row.operator( "i3d.paneladdshader_buttonload")

        # "Tools" tab
        #-----------------------------------------
        elif 'tools' == context.scene.I3D_UIexportSettings.UI_settingsMode:
            box = layout.box()
            row = box.row()

            row.prop(   context.scene.I3D_UIexportSettings,
                "UI_customTools",
                text = "Custom Tools",
                icon='TRIA_DOWN' if context.scene.I3D_UIexportSettings.UI_customTools else 'TRIA_RIGHT',
                icon_only = False,
                emboss = False )

            row = box.row()
            if context.scene.I3D_UIexportSettings.UI_customTools:
                # row.label(text="export DDS")
                col = row.column()

                row = col.row(align = True)
                row.operator("i3d.selectiontoorigin", text="SelectionToOrigin")
                row.operator("i3d.facenormaltoorigin", text="FaceNormalToOrigin")

                row = col.row(align = True)
                row.operator("i3d.freezetranslation", text="FreezeTranslation")
                row.operator("i3d.freezerotation", text="FreezeRotation")

                row = col.row(align = True)
                row.operator("i3d.createempty", text="Create Empty")
                row.operator("i3d.alignyaxis", text="AlignYAxis")

                col.operator("i3d.paneltools_button", text="Export Object Data Texture").state = 1
                try:
                #TODO: smart loop for UI elements
                    row = col.row(align = True)
                    row.operator("i3d.motionpathpopup")
                    row.operator("i3d.motionpathobjectpopup")

                    row = col.row(align = True)
                    row.operator("i3d.vertexcolorpopup")
                    row.operator("i3d.splinetoolpopup")
                except:
                    pass

            #-----------------------------------------

        # row = layout.row( )
        # row.operator( "i3d.panelexport_buttonclose", icon = 'X' )

    def getMaterials(self, context):
        result = [(mat.name, mat.name, "", "NONE", i + 1) for i, mat in enumerate(bpy.data.materials)]
        result.insert(0, ("None", "None", "", "NONE", 0))
        return result

    def getShadersFromDirectory(self, context):
        """
        Reads the directory and returns a List for the Shader enumerate

        :returns: a Tuple formatted for an bpy.EnumProperty, default is (("None","None","None"))
        """

        dirPath = bpy.context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation.replace("$", bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation)
        dirPath = os.path.abspath(dirPath)
        # print(dirPath)
        try:
            onlyfiles = [f for f in listdir(dirPath) if isfile(join(dirPath, f)) if f.endswith("Shader.xml")]
            fileTuple = tuple()
            # fileTuple = fileTuple + (("None","None","None", 0),)
            index = 0
            for file in onlyfiles:
                fileTuple = fileTuple + ((file,file,file,index),)
                index += 1
            if len(onlyfiles) == 0:
                return (("None","None","None", 0),)
            return fileTuple
        except FileNotFoundError as e:
            # print(e)
            # print("file not found")
            return (("None","None","None", 0),)  #Problem
        except Exception as e:
            print(e)
            print("f2")
            return (("None","None","None", 0),)  #Problem


    def getShaderVariations(self,context):
        """
        Reads the variation property from the shader file and returns the data to the variation enumerate

        :returns: a Tubple formatted for an bpy.EnumProperty, default is (("None","None","None"),)
        """

        shaderData = extractXMLShaderData()
        variationsTuple = (("None","None","None"),)
        if shaderData != None:
            for variation in shaderData["variations"].keys():
                variationsTuple = variationsTuple + ((variation,variation,variation),)
        return variationsTuple


    def getActiveObjectType(self,context):      #unused
        """ returns the type of the active object """

        objName = context.scene.I3D_UIexportSettings.UI_ActiveObjectName
        return bpy.data.objects[objName].type

    def updateXMLconfigId(self,context):
        """ Updates the XML configuration Id of the active object to the manually set value """
        objName = context.scene.I3D_UIexportSettings.UI_ActiveObjectName
        if objName in bpy.data.objects:
            bpy.data.objects[objName]["I3D_XMLconfigID"] = context.scene.I3D_UIexportSettings.I3D_XMLConfigIdentification
            # bpy.ops.i3d.panelupdatexmli3dmapping()

    def updateXMLconfigBool(self, context):
        """ Updates the XML configuration checkbox of the active object to the manually set value """

        objects = selectionUtil.getSelectedObjects(context)
        for object in objects:
            objName = object.name
            if object.name in bpy.data.objects:
                # while enabeling the xml identifier we directly set the node name as identifier
                if "I3D_XMLconfigBool" not in bpy.data.objects[object.name] or not bpy.data.objects[object.name]["I3D_XMLconfigBool"]:
                    bpy.data.objects[object.name]["I3D_XMLconfigID"] = dccBlender.getFormattedNodeName(object.name)

                bpy.data.objects[objName]["I3D_XMLconfigBool"] = context.scene.I3D_UIexportSettings.I3D_XMLConfigExport

    def sceneObjectItems(self, context):
        """
        Returns a listing of all objects in the scene, except the loaded Node

        :returns: a list of Tuples formatted for a bpy.EnumProperty
        """
        objectList = [("None","None","None")]
        try:
            objectList = [(obj.name,obj.name,obj.name) for obj in context.scene.objects]
            #objectList.remove((context.scene.I3D_UIexportSettings.I3D_nodeName,context.scene.I3D_UIexportSettings.I3D_nodeName,context.scene.I3D_UIexportSettings.I3D_nodeName))
            objectList.append(("None","None","None"))
        except:
            pass
        return objectList
    
class I3D_UIMaterialTemplateProperties(bpy.types.PropertyGroup):
    fileLocation : bpy.props.StringProperty()
    
    @classmethod
    def register( cls ):
        bpy.types.Scene.I3D_UIMaterialTemplateProperties = bpy.props.PointerProperty(
            name = "I3D UI Material Template Properties",
            type =  cls,
            description = "I3D UI Material Template Properties"
        )
    @classmethod
    def unregister( cls ):
        if bpy.context.scene.get( 'I3D_UIMaterialTemplateProperties' ):  del bpy.context.scene[ 'I3D_UIMaterialTemplateProperties' ]
        try:    del bpy.types.Scene.I3D_UIMaterialTemplateProperties
        except: pass

class I3D_OT_MaterialTemplateCategoryMenu(bpy.types.Operator):
    bl_idname = "i3d.material_template_category_menu_entry_selected"
    bl_label = "Select material template category menu item"

    categoryName: bpy.props.StringProperty()

    def execute(self, context):
        global g_selectedMaterialTemplateCategory
        if g_selectedMaterialTemplateCategory == self.categoryName:
            g_selectedMaterialTemplateCategory = None
        else:
            g_selectedMaterialTemplateCategory = self.categoryName
        #self.report({"INFO"}, "{} material template category selected".format(self.categoryName))
        return {'FINISHED'}

class I3D_OT_MaterialTemplateCategoryMenuEntryExpand(bpy.types.Operator):
    bl_idname = "i3d.material_template_category_menu_entry_expand"
    bl_label = "Expand material template category menu item"
    
    categoryName: bpy.props.StringProperty()

    def execute(self, context):
        categoryPath = self.categoryName.split("_")

        currentMaterialTemplateCategoryDict = g_loadedMaterialTemplates
        for category in categoryPath:
            currentMaterialTemplateCategoryDict = currentMaterialTemplateCategoryDict[category]

        currentMaterialTemplateCategoryDict["expanded"] = not currentMaterialTemplateCategoryDict["expanded"]

        #self.report({"INFO"}, "{} material template category expanded".format(self.categoryName))
        return {'FINISHED'}

class I3D_PT_MaterialTemplates(bpy.types.Panel):
    """GUI Panel for the GIANTS Material Templates Library"""
    bl_idname = "I3D_PT_MaterialTemplates"
    bl_label = "GIANTS Material Templates Library"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PMR GIANTS I3D Exporter"

    def renderCategoryMenuEntry(self, context, parentBox, category, categoryTitle, categoryOpen, childList):
        hasChildren = len(childList) > 2 # expanded, thumbnails

        row = parentBox.row()

        iconName = "NONE"
        if hasChildren:
            if categoryOpen:
                iconName = "TRIA_DOWN"
            else:
                iconName = "TRIA_RIGHT"

            o = row.operator("i3d.material_template_category_menu_entry_expand", text = "", icon = iconName)
            o.categoryName = category
        else:
            row.label(text="", icon="DOT")

        o = row.operator("i3d.material_template_category_menu_entry_selected", text = categoryTitle, depress = g_selectedMaterialTemplateCategory == category)
        o.categoryName = category

        if not hasChildren or not categoryOpen:
            return
        
        childBoxRow = parentBox.row()
        childBox = childBoxRow.box()
        for subCategoryName, subCategory in childList.items():
            if subCategoryName == 'templates' or subCategoryName == "expanded" or subCategoryName == "thumbnails":
                continue
            self.renderCategoryMenuEntry(context, childBox, category + "_" + subCategoryName, subCategoryName, childList["expanded"], subCategory)

    def renderPreviewThumbnails(self, previewGrid, categoryDict):
        previewCollection = categoryDict["thumbnails"]
        for materialTemplateName, materialTemplate in previewCollection.items():
            cell = previewGrid.column().box()
            cell.template_icon(materialTemplate.icon_id, scale=10)
            o = cell.operator("i3d.apply_material_template_to_selection")
            o.templateName = materialTemplateName

        for subCategory, subCategoryDict in categoryDict.items():
            if subCategory == "templates" or subCategory == "expanded" or subCategory == "thumbnails":
                continue
            self.renderPreviewThumbnails(previewGrid, subCategoryDict)

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.prop(context.scene.I3D_UIMaterialTemplateProperties, "fileLocation", text = "Templates XML File")
        row.operator("i3d.openfolderfilebrowser", icon='FILEBROWSER',text = "").state = 2

        row = layout.row()
        menuLayout = row.split(factor = 0.2)
        menuBox = menuLayout.box()
        previewBox = menuLayout.box()

        for subCategoryName, subCategory in g_loadedMaterialTemplates.items():
            if subCategoryName == 'templates' or subCategoryName == 'expanded' or subCategoryName == "thumbnails":
                continue
            self.renderCategoryMenuEntry(context, menuBox, subCategoryName, subCategoryName, subCategory["expanded"], subCategory)

        previewGrid = previewBox.grid_flow()

        currentMaterialTemplateCategoryDict = g_loadedMaterialTemplates

        if g_selectedMaterialTemplateCategory is not None:
            selectedCategoryPath = g_selectedMaterialTemplateCategory.split("_")
            for category in selectedCategoryPath:
                currentMaterialTemplateCategoryDict = currentMaterialTemplateCategoryDict[category]
                
            self.renderPreviewThumbnails(previewGrid, currentMaterialTemplateCategoryDict)
        else:
            for category, categoryDict in currentMaterialTemplateCategoryDict.items():
                if category == "templates" or category == "expanded" or category == "thumbnails":
                    continue
                self.renderPreviewThumbnails(previewGrid, categoryDict)

#-------------------------------------------------------------------------------
# Buttons Operators
#-------------------------------------------------------------------------------

class I3D_OT_BitmaskEditor(bpy.types.Operator):
    bl_idname = "i3d.bitmaskeditor"
    bl_label = "Bitmask Editor"

    def updtVal(self, context):
        str_dec = stringUtil.int2string_base(int(self.mask_value,10),10)
        str_hex = stringUtil.int2string_base(int(self.mask_value,10),16)
        str_bin = stringUtil.int2string_base(int(self.mask_value,10),2)
        bitList = [self.bit0,self.bit1,self.bit2,self.bit3,self.bit4,self.bit5,self.bit6,self.bit7,self.bit8,self.bit9,self.bit10,self.bit11,self.bit12,self.bit13,self.bit14,self.bit15,self.bit16,
                    self.bit17,self.bit18,self.bit19,self.bit20,self.bit21,self.bit22,self.bit23,self.bit24,self.bit25,self.bit26,self.bit27,self.bit28,self.bit29,self.bit30,self.bit31]
        bitList = list(map(int, bitList))
        bitList.reverse()
        strList = list(map(str,bitList))
        str_bit = ''.join(strList)
        if self.dec_mask != str_dec:
            self.dec_mask = str_dec
        if self.hex_mask != str_hex:
            self.hex_mask = str_hex
        if self.bin_mask != str_bin:
            self.bin_mask = str_bin
        compare_str_bit = list(str_bin)
        compare_str_bit.reverse()
        compare_str_bit = compare_str_bit[:32] + ['0']*(32- len(compare_str_bit))
        compare_str_bit = ''.join(compare_str_bit)
        if not str_bit == compare_str_bit:
            val_list = list(map(bool,list(map(int,list(compare_str_bit)))))
            self.bit0 = val_list[0]; self.bit1 = val_list[1]; self.bit2 = val_list[2]; self.bit3 = val_list[3]
            self.bit4 = val_list[4]; self.bit5 = val_list[5]; self.bit6 = val_list[6]; self.bit7 = val_list[7]
            self.bit8 = val_list[8]; self.bit9 = val_list[9]; self.bit10 = val_list[10]; self.bit11 = val_list[11]; self.bit12 = val_list[12]; self.bit13 = val_list[13]; self.bit14 = val_list[14]; self.bit15 = val_list[15]
            self.bit16 = val_list[16]; self.bit17 = val_list[17]; self.bit18 = val_list[18]; self.bit19 = val_list[19]; self.bit20 = val_list[20]; self.bit21 = val_list[21]; self.bit22 = val_list[22]; self.bit23 = val_list[23]
            self.bit24 = val_list[24]; self.bit25 = val_list[25]; self.bit26 = val_list[26]; self.bit27 = val_list[27]; self.bit28 = val_list[28]; self.bit29 = val_list[29]; self.bit30 = val_list[30]; self.bit31 = val_list[31]

    def updtBin(self, context):
        try:
            if int(self.mask_value,10) == int(self.bin_mask,base=2) or len(list(self.bin_mask)) > self.bitCount:
                return
            self.mask_value = str(int(self.bin_mask,base=2))
        except Exception as e:
            pass
            # self.report({'WARNING'}, str(e))

    def updtHex(self, context):
        try:
            if int(self.mask_value,10) == int(self.hex_mask,base=16) or len(list(self.hex_mask)) >  self.bitCount/4:
                return
            self.mask_value = str(int(self.hex_mask,base=16))
        except Exception as e:
            pass
            # self.report({'WARNING'}, str(e))

    def updtDec(self, context):
        try:
            if int(self.mask_value,10) == int(self.dec_mask, base=10) or int(self.dec_mask, base=10) > int(2**self.bitCount)-1:
                return
            self.mask_value = str(int(self.dec_mask, base=10))
        except Exception as e:
            print(e)
            pass
            # self.report({'WARNING'}, str(e))

    def updtBit(self,context):
        bitList = [self.bit0,self.bit1,self.bit2,self.bit3,self.bit4,self.bit5,self.bit6,self.bit7,self.bit8,self.bit9,self.bit10,self.bit11,self.bit12,self.bit13,self.bit14,self.bit15,
                self.bit16,self.bit17,self.bit18,self.bit19,self.bit20,self.bit21,self.bit22,self.bit23,self.bit24,self.bit25,self.bit26,self.bit27,self.bit28,self.bit29,self.bit30,self.bit31]
        bitList = list(map(int, bitList))
        bitList.reverse()
        strList = list(map(str,bitList))
        str_bit = ''.join(strList)
        # print(str_bit)
        if int(self.mask_value,10) == int(str_bit,base=2):
            return
        self.mask_value = str(int(str_bit,base=2))


    bitCount : bpy.props.IntProperty(default=32)
    state      : bpy.props.IntProperty()
    mask_value: bpy.props.StringProperty(name="Value",update = updtVal)
    hex_mask: bpy.props.StringProperty(name="Bit Mask (Hex)",update=updtHex)
    dec_mask: bpy.props.StringProperty(name="Bit Mask (Dec)",update=updtDec)
    bin_mask: bpy.props.StringProperty(name="Bit Mask (Bin)",update=updtBin)
    bit0: bpy.props.BoolProperty(name="0",update=updtBit); bit1: bpy.props.BoolProperty(name="1",update=updtBit);bit2: bpy.props.BoolProperty(name="2",update=updtBit);bit3: bpy.props.BoolProperty(name="3",update=updtBit)
    bit4: bpy.props.BoolProperty(name="4",update=updtBit);bit5: bpy.props.BoolProperty(name="5",update=updtBit);bit6: bpy.props.BoolProperty(name="6",update=updtBit);bit7: bpy.props.BoolProperty(name="7",update=updtBit)
    bit8: bpy.props.BoolProperty(name="8",update=updtBit);bit9: bpy.props.BoolProperty(name="9",update=updtBit);bit10: bpy.props.BoolProperty(name="10",update=updtBit);bit11: bpy.props.BoolProperty(name="11",update=updtBit)
    bit12: bpy.props.BoolProperty(name="12",update=updtBit);bit13: bpy.props.BoolProperty(name="13",update=updtBit);bit14: bpy.props.BoolProperty(name="14",update=updtBit);bit15: bpy.props.BoolProperty(name="15",update=updtBit)
    bit16: bpy.props.BoolProperty(name="16",update=updtBit);bit17: bpy.props.BoolProperty(name="17",update=updtBit);bit18: bpy.props.BoolProperty(name="18",update=updtBit);bit19: bpy.props.BoolProperty(name="19",update=updtBit)
    bit20: bpy.props.BoolProperty(name="20",update=updtBit);bit21: bpy.props.BoolProperty(name="21",update=updtBit);bit22: bpy.props.BoolProperty(name="22",update=updtBit);bit23: bpy.props.BoolProperty(name="23",update=updtBit)
    bit24: bpy.props.BoolProperty(name="24",update=updtBit);bit25: bpy.props.BoolProperty(name="25",update=updtBit);bit26: bpy.props.BoolProperty(name="26",update=updtBit);bit27: bpy.props.BoolProperty(name="27",update=updtBit)
    bit28: bpy.props.BoolProperty(name="28",update=updtBit);bit29: bpy.props.BoolProperty(name="29",update=updtBit);bit30: bpy.props.BoolProperty(name="30",update=updtBit);bit31: bpy.props.BoolProperty(name="31",update=updtBit)

    def execute(self, context):
        if self.state == 0:
            context.scene.I3D_UIexportSettings.I3D_weatherMask = self.mask_value
        elif self.state == 1:
            context.scene.I3D_UIexportSettings.I3D_weatherPreventMask = self.mask_value
        elif self.state == 2:
            context.scene.I3D_UIexportSettings.I3D_viewerSpacialityMask = self.mask_value
        elif self.state == 3:
            context.scene.I3D_UIexportSettings.I3D_viewerSpacialityPreventMask = self.mask_value
        return {'FINISHED'}

    def invoke(self, context, event):
        #do initialzation
        wm = context.window_manager
        if self.state == 0:
            if not context.scene.I3D_UIexportSettings.I3D_weatherMask.isdigit():
                self.report({'WARNING'}, "{} is not an integer".format(context.scene.I3D_UIexportSettings.I3D_weatherMask))
                return {'CANCELLED'}
            self.mask_value = context.scene.I3D_UIexportSettings.I3D_weatherMask
            self.bitCount = 32
        elif self.state == 1:
            if not context.scene.I3D_UIexportSettings.I3D_weatherPreventMask.isdigit():
                self.report({'WARNING'}, "{} is not an integer".format(context.scene.I3D_UIexportSettings.I3D_weatherPreventMask))
                return {'CANCELLED'}
            self.mask_value = context.scene.I3D_UIexportSettings.I3D_weatherPreventMask
            self.bitCount = 32
        elif self.state == 2:
            if not context.scene.I3D_UIexportSettings.I3D_viewerSpacialityMask.isdigit():
                self.report({'WARNING'}, "{} is not an integer".format(context.scene.I3D_UIexportSettings.I3D_viewerSpacialityMask))
                return {'CANCELLED'}
            self.mask_value = context.scene.I3D_UIexportSettings.I3D_viewerSpacialityMask
            self.bitCount = 32
        elif self.state == 3:
            if not context.scene.I3D_UIexportSettings.I3D_viewerSpacialityPreventMask.isdigit():
                self.report({'WARNING'}, "{} is not an integer".format(context.scene.I3D_UIexportSettings.I3D_viewerSpacialityPreventMask))
                return {'CANCELLED'}
            self.mask_value = context.scene.I3D_UIexportSettings.I3D_viewerSpacialityPreventMask
            self.bitCount = 32
        return wm.invoke_props_dialog(self,width=400)

    def draw(self,context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "hex_mask")
        col.prop(self, "dec_mask")
        col.prop(self, "bin_mask")
        box = layout.box()
        if self.bitCount >= 32:
            row = box.row()
            row.prop(self,'bit31')
            row.prop(self,'bit30')
            row.prop(self,'bit29')
            row.prop(self,'bit28')
            row.prop(self,'bit27')
            row.prop(self,'bit26')
            row.prop(self,'bit25')
            row.prop(self,'bit24')
        if self.bitCount >= 24:
            row = box.row()
            row.prop(self,'bit23')
            row.prop(self,'bit22')
            row.prop(self,'bit21')
            row.prop(self,'bit20')
            row.prop(self,'bit19')
            row.prop(self,'bit18')
            row.prop(self,'bit17')
            row.prop(self,'bit16')
        if self.bitCount >= 16:
            row = box.row()
            row.prop(self,'bit15')
            row.prop(self,'bit14')
            row.prop(self,'bit13')
            row.prop(self,'bit12')
            row.prop(self,'bit11')
            row.prop(self,'bit10')
            row.prop(self,'bit9')
            row.prop(self,'bit8')
        row = box.row()
        if self.bitCount >= 8:
            row.prop(self,'bit7')
            row.prop(self,'bit6')
            row.prop(self,'bit5')
            row.prop(self,'bit4')
        if self.bitCount >= 4:
            row.prop(self,'bit3')
            row.prop(self,'bit2')
            row.prop(self,'bit1')
            row.prop(self,'bit0')


class I3D_OT_modal_active_object(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "i3d.active_object"
    bl_label = "Active Object"

    # @classmethod
    # def poll(cls, context):
    #     return context.area.type == 'OUTLINER'

    def modal(self, context, event):
        global g_disableSelectedMaterialEnumUpdateCallback

        currentObjName = bpy.data.scenes[context.scene.name].I3D_UIexportSettings.UI_ActiveObjectName

        activeObject = None
        objects = selectionUtil.getSelectedObjects(context)
        if len(objects) > 0:
            activeObject = objects[0]

        if activeObject is not None:
            objName = activeObject.name
            if currentObjName != objName:
                #current obj update
                bpy.data.scenes[context.scene.name].I3D_UIexportSettings.UI_ActiveObjectName = objName
                bpy.data.scenes[context.scene.name].I3D_UIexportSettings.UI_PrevActiveObjectName = currentObjName
                currentObjName = objName

                if context.scene.I3D_UIexportSettings.UI_autoAssign:
                    dcc.I3DSaveObjectAttributes()
                    dcc.I3DLoadObjectAttributes()
        else:
            currentObjName = 'empty'
            bpy.data.scenes[context.scene.name].I3D_UIexportSettings.UI_ActiveObjectName = currentObjName

        if currentObjName == 'empty':
            g_disableSelectedMaterialEnumUpdateCallback = True
            bpy.data.scenes[context.scene.name].I3D_UIexportSettings.I3D_selectedMaterialEnum = "None"
            g_disableSelectedMaterialEnumUpdateCallback = False
            return {'PASS_THROUGH'}
        
        # Update selected material
        activeMat = bpy.data.objects[currentObjName].active_material
        g_disableSelectedMaterialEnumUpdateCallback = True
        bpy.data.scenes[context.scene.name].I3D_UIexportSettings.I3D_selectedMaterialEnum = activeMat.name if activeMat != None else "None"
        g_disableSelectedMaterialEnumUpdateCallback = False

        if currentObjName not in bpy.data.objects:
            return {'PASS_THROUGH'}

        #UI to local attribute data transfer update and
        if not "I3D_XMLconfigID" in bpy.data.objects[currentObjName]:
            bpy.data.objects[currentObjName]["I3D_XMLconfigID"] = currentObjName    #set default

        # while the node id is disabled we show the object name, which is set by default after activating the node id
        if "I3D_XMLconfigBool" in bpy.data.objects[currentObjName] and bpy.data.objects[currentObjName]["I3D_XMLconfigBool"] == 1:
            bpy.data.scenes[context.scene.name].I3D_UIexportSettings.I3D_XMLConfigIdentification = bpy.data.objects[currentObjName]["I3D_XMLconfigID"]
        else:
            bpy.data.scenes[context.scene.name].I3D_UIexportSettings.I3D_XMLConfigIdentification = currentObjName

        #update checkbox
        if not "I3D_XMLconfigBool" in bpy.data.objects[currentObjName]:
            bpy.data.objects[currentObjName]["I3D_XMLconfigBool"] = False   #set default
        context.scene.I3D_UIexportSettings.I3D_XMLConfigExport = (bpy.data.objects[currentObjName]["I3D_XMLconfigBool"]  == 1)
        return {'PASS_THROUGH'}

    def execute(self, context):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

class I3D_OT_modal_predef_check(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "i3d.predef_check"
    bl_label = "Predefined has change check"

    def modal(self, context, event):

        if event.type in {"LEFTMOUSE","RET","INBETWEEN_MOUSEMOVE","NUMPAD_ENTER"}:# and event.value == "RELEASE":      #does not work since modal notification is before change of active object
            hasNoChange = True
            predefineName =  context.scene.I3D_UIexportSettings.I3D_selectedPredefined
            physics = dcc.UIgetPredefinePhysicItems(self, context)
            predefinedTagList = [tup[0] for tup in physics if tup[1] == predefineName]
            if len(predefinedTagList) > 0:
                predefinedTag = predefinedTagList[0]
                if predefinedTag in [tup[0] for tup in physics]:
                    for key, value in dcc.I3DgetPredefinePhysicAttr(predefinedTag).items():
                        # print("k: {}, v: {}, curr: {}, same: {}".format(key,value,context.scene.I3D_UIexportSettings[key],value == context.scene.I3D_UIexportSettings[key]))
                        hasNoChange = hasNoChange and (value == context.scene.I3D_UIexportSettings[key])
            nonPhysics = dcc.UIgetPredefineNonPhysicItems(self, context)
            predefinedTagList = [tup[0] for tup in nonPhysics if tup[1] == predefineName]
            if len(predefinedTagList) > 0:
                predefinedTag = predefinedTagList[0]
                if predefinedTag in [tup[0] for tup in nonPhysics]:
                    for key, value in dcc.I3DgetPredefineNonPhysicAttr(predefinedTag).items():
                        if key in context.scene.I3D_UIexportSettings.keys():
                            #print("k: {}, v: {}, curr: {}, same: {}".format(key,value,context.scene.I3D_UIexportSettings[key],value == context.scene.I3D_UIexportSettings[key]))
                            hasNoChange = hasNoChange and (value == context.scene.I3D_UIexportSettings[key])
            # print("hasChanged? {}".format(not hasNoChange))
            context.scene.I3D_UIexportSettings.I3D_predefHasChanged = not hasNoChange

        return {'PASS_THROUGH'}

    def execute(self, context):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

class I3D_OT_PanelUpdateXMLi3dmapping( bpy.types.Operator):
    """ Textfield Operator """

    bl_idname= "i3d.panelupdatexmli3dmapping"
    bl_label = "XML i3d mapping check"
    bl_options = {'REGISTER'}

    def execute(self,context):
        """ purely to have reasonable user feedback for xml i3d mappings """

        currentObjName = bpy.data.scenes[context.scene.name].I3D_UIexportSettings.UI_ActiveObjectName
        currentObject = bpy.data.objects[currentObjName]
        currentIDDict = {currentObject["I3D_XMLconfigID"] : currentObject.name}
        # print(self.state)
        for (objName,obj) in bpy.data.objects.items():
            if obj == currentObject:
                continue
            if 'I3D_XMLconfigID' in obj.keys() and 'I3D_XMLconfigBool' in obj.keys():
                if not obj['I3D_XMLconfigBool']:
                    continue
                if obj["I3D_XMLconfigID"] in currentIDDict:
                    # obj is a duplicate name of currentObject's i3d id
                    # currentIDDict[obj["I3D_XMLconfigID"]] = objName
                    self.report({'WARNING'},  currentObject.name + " has a Duplicate i3dMapping ID \"" +context.scene.I3D_UIexportSettings.I3D_XMLConfigIdentification + "\" with Object: "+ objName)
        return {'FINISHED'}

class I3D_OT_PanelExport_ButtonAttr( bpy.types.Operator ):
    """ Multi purpose GUI Button element for Node manipulation"""

    bl_idname  = "i3d.panelexport_buttonattr"
    bl_label   = "Attributes"
    state      : bpy.props.IntProperty()

    def execute( self, context ):
        if   1 == self.state:
            dcc.I3DLoadObjectAttributes()
        elif 2 == self.state:
            dcc.I3DSaveObjectAttributes()
        elif 3 == self.state:
            dcc.I3DRemoveObjectAttributes()
        elif 4 == self.state:
            dcc.I3DApplySelectedAttributes()
        elif 5 == self.state:
            dcc.I3DRemoveSelectedAttributes()   #restore default
        return {'FINISHED'}

class I3D_OT_PanelExport_ButtonExport( bpy.types.Operator ):
    """ Multi purpose GUI Button element for Export options"""

    bl_idname  = "i3d.panelexport_buttonexport"
    bl_label   = "Export"
    state      : bpy.props.IntProperty()

    def execute( self, context ):
        # bpy.ops.wm.console_toggle()     #DEBUG command

        frame = bpy.context.scene.frame_current
        try:
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set ( mode = 'OBJECT' ) #export in object mode
        except:
            current_mode = 'OBJECT'

        bpy.context.scene.frame_set(0)      #export bind pose

        if context.scene.I3D_UIexportSettings.I3D_generateexporterprofile:

            #kb adding some simple code to generate a profile of the export we have attempted. 
            # this will allow people to fire over profiles when they suspect something has slowed down

            if context.scene.I3D_UIexportSettings.I3D_exportUseSoftwareFileName:
                profileExportfileLocation = bpy.data.filepath
            else :
                profileExportfileLocation = bpy.path.abspath(bpy.context.scene.I3D_UIexportSettings.I3D_exportFileLocation)

            profileExportfileLocation = os.path.splitext(profileExportfileLocation)[0] + '.profile'
  
            targetdir = os.path.dirname(profileExportfileLocation)                                                        
            if not os.path.exists(targetdir):
                os.makedirs(targetdir)
 
            # Ensure the function is in the correct context
            def wrapped_ExportAll():
                i3d_export.I3DExportAll()
 
            def wrapped_ExportSelected():
                i3d_export.I3DExportSelected()
 
            def wrapped_ExportUpdateXML():
                i3d_export.I3DUpdateXML()
 
            if   1 == self.state:
                cProfile.runctx('wrapped_ExportAll()', globals(), locals(), profileExportfileLocation)
            elif 2 == self.state:
                cProfile.runctx('wrapped_ExportSelected()', globals(), locals(), profileExportfileLocation)
            elif 3 == self.state:
                cProfile.runctx('wrapped_ExportUpdateXML()', globals(), locals(), profileExportfileLocation)
            
            p = pstats.Stats(profileExportfileLocation)
            p.sort_stats('cumulative').print_stats(10)
        else :
            if   1 == self.state:
                i3d_export.I3DExportAll()
            elif 2 == self.state:
                i3d_export.I3DExportSelected()
            elif 3 == self.state:
                i3d_export.I3DUpdateXML()

        bpy.context.scene.frame_set(frame)
        try:
            bpy.ops.object.mode_set ( mode = current_mode )
        except:
            pass
         #Info Log output
        for header in logUtil.ActionLog.header:
            self.report(header[0],header[1])
        for message in logUtil.ActionLog.message:
            self.report(message[0],message[1])
        logUtil.ActionLog.reset()

        currentIDDict = {}
        for (objName,obj) in bpy.data.objects.items():
            if 'I3D_XMLconfigID' in obj.keys() and 'I3D_XMLconfigBool' in obj.keys():
                if not obj['I3D_XMLconfigBool']:
                    continue
                if obj["I3D_XMLconfigID"] in currentIDDict :
                    self.report({'WARNING'}, "Duplicate i3dMappings: Object: "+ objName + ", i3dmapping: " + obj["I3D_XMLconfigID"])
                    self.report({'WARNING'}, "Duplicate i3dMappings: Object: "+ currentIDDict[obj["I3D_XMLconfigID"]] + ", i3dmapping: " + obj["I3D_XMLconfigID"])
                else:
                    currentIDDict[obj["I3D_XMLconfigID"]] = objName

        return {'FINISHED'}

class I3D_OT_PanelRemoveXMLPath_ButtonRemove( bpy.types.Operator):
    """ GUI element Button to remove XML File path """

    bl_idname= "i3d.panelremovexmlpath_buttonremove"
    bl_label = "XMLPath"
    state : bpy.props.StringProperty()

    def execute(self,context):
        context.scene.I3D_UIexportSettings.I3D_updateXMLFilePath = context.scene.I3D_UIexportSettings.I3D_updateXMLFilePath.replace(";{};;".format(self.state), "")
        return {'FINISHED'}

class I3D_OT_PanelAddShader_ButtonLoad( bpy.types.Operator):
    """ GUI element Button to Load custom Shader settings from the Node into the Exporter GUI"""

    bl_idname= "i3d.paneladdshader_buttonload"
    bl_label = "Load Shader"

    def execute(self,context):
        """ Creates and registers dynamic classes for dynamic GUI elements """

        global g_dynamicGUIClsDict

        #delete previous values
        if bpy.context.scene.get( 'I3D_UIShaderParameters' ):
            del bpy.context.scene[ 'I3D_UIShaderParameters' ]
        try:
            del bpy.types.Scene.I3D_UIShaderParameters
        except:
            pass
        if bpy.context.scene.get( 'I3D_UIShaderTextures' ):
            del bpy.context.scene[ 'I3D_UIShaderTextures' ]
        try:
            del bpy.types.Scene.I3D_UIShaderTextures
        except:
            pass
        #delete previous gui elements
        for dynamicClass in g_dynamicGUIClsDict.values():
            bpy.utils.unregister_class(dynamicClass)

        g_dynamicGUIClsDict = {}
        try:
            actObjName = context.active_object.name
        except:
            try:
                actObjName = dccBlender.getSelectedNodes()[0]
            except:
                actObjName = bpy.data.scenes[context.scene.name].I3D_UIexportSettings.UI_PrevActiveObjectName
        activeObject = bpy.data.objects[actObjName]
        materialObj = activeObject.active_material
        shaderData =  {"parameters": {},"textures": {}, "parameterTemplates": {} , "parameterTypes" : {}}
        if materialObj:
            for name, value in materialObj.items():
                if name.startswith("customParameterTemplate"):
                    parts = name.split("_")
                    templateId = parts[1]
                    subTemplateId = parts[2]
                    if templateId not in shaderData["parameterTemplates"]:
                        shaderData["parameterTemplates"][templateId] = {}
                    shaderData["parameterTemplates"][templateId][subTemplateId] = value
                elif name.startswith("customParameter"):
                    shaderData["parameters"][name.split("_")[1]] = value
                elif name == "customShader":
                    # print("value: {}".format(value))
                    try:
                        if value[0] == '$':
                            fullShaderPath = value
                            fullShaderPath = fullShaderPath.replace("/", os.sep)
                            fullShaderPath = fullShaderPath.replace("\\",os.sep)
                        elif os.path.isfile(value):
                            fullShaderPath = pathUtil.resolvePath(value, referenceDirectory = None, targetDirectory = None)
                        else:
                            fullShaderPath = pathUtil.resolvePath(value, referenceDirectory = bpy.path.abspath("//"), targetDirectory = None)
                    except pathUtil.InputError as e:
                        self.report({'WARNING'},e.message)
                        return {'CANCELLED'}
                    shaderXML = fullShaderPath.split(os.sep)[-1]
                    shaderPath = fullShaderPath.rsplit(os.sep,1)[0]
                    # print("file: {}".format(shaderXML))
                    # print("path: {}".format(shaderPath))
                elif name == "customShaderVariation":
                    shaderVariation = value
                elif name.startswith("customTexture"):
                    shaderData["textures"][name.split("_")[1]] = value

        # if materialObj and "customShader" in materialObj:
        #     value = materialObj["customShader"]
        #     try:
        #         if value[0] == '$':
        #             fullShaderPath = value
        #             fullShaderPath = fullShaderPath.replace("/", os.sep)
        #             fullShaderPath = fullShaderPath.replace("\\",os.sep)
        #         elif os.path.isfile(value):
        #             fullShaderPath = pathUtil.resolvePath(value, referenceDirectory = None, targetDirectory = None)
        #         else:
        #             fullShaderPath = pathUtil.resolvePath(value, referenceDirectory = bpy.path.abspath("//"), targetDirectory = None)
        #     except pathUtil.InputError as e:
        #         self.report({'WARNING'},e.message)
        #         return {'CANCELLED'}
        #     shaderXML = fullShaderPath.split(os.sep)[-1]
        #     shaderPath = fullShaderPath.rsplit(os.sep,1)[0]

        #previousShaderPath = context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation
        #previousShaderEnum = context.scene.I3D_UIexportSettings.I3D_shaderEnum
        try:
            #context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation = shaderPath    #set path
            context.scene.I3D_UIexportSettings.I3D_shaderEnum = shaderXML
            fileShaderData = extractXMLShaderData()         #get data from path
        #except UnboundLocalError as e:
            # print(e)
            # print("invalid shader file path")
            #context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation = previousShaderPath    #set path
            #context.scene.I3D_UIexportSettings.I3D_shaderEnum = previousShaderEnum
            #fileShaderData = extractXMLShaderData()         #get data from path
        except:
            context.scene.I3D_UIexportSettings.I3D_shaderEnum = [t[0] for t in I3D_PT_PanelExport.getShadersFromDirectory(self,context)][0]
            fileShaderData = extractXMLShaderData()

        if fileShaderData:
            # TODO(jdellsperger): It would be better to initialize the dynamic gui classes with the function below and
            # only set the proper values here.
            #updateDynamicUIClassesForShaderParameters(fileShaderData, ["base"]) # TODO(jdellsperger): Determine actual variation groups
            dynamicGUIDict = {}
            for name, value in fileShaderData["parameters"].items():
                if name in shaderData["parameters"]:
                    boolValue = True
                    value = shaderData["parameters"][name]
                else:
                    boolValue = False
                try:
                    valueList = [float(x) for x in value.strip().split(" ")]
                except Exception as e:
                    print(e)
                    valueList = []
                valueList = valueList + [1.0,1.0,1.0,1.0]
                dynamicGUIDict.update({
                        name+"Bool": bpy.props.BoolProperty(default= boolValue),
                        name+"_0": bpy.props.FloatProperty(default = valueList[0] , precision = dcc.FLOAT_PRECISION ),
                        name+"_1": bpy.props.FloatProperty(default = valueList[1] , precision = dcc.FLOAT_PRECISION ),
                        name+"_2": bpy.props.FloatProperty(default = valueList[2] , precision = dcc.FLOAT_PRECISION ),
                        name+"_3": bpy.props.FloatProperty(default = valueList[3] , precision = dcc.FLOAT_PRECISION )
                        # name: bpy.props.StringProperty(default= value)
                        })

            paramClss = type('I3D_UIShaderParameters', (bpy.types.PropertyGroup,), {'__annotations__': dynamicGUIDict})
            bpy.utils.register_class(paramClss)     #set new gui elements
            bpy.types.Scene.I3D_UIShaderParameters = bpy.props.PointerProperty(type=paramClss)
            dynamicGUIDict = {}
            for name, value in fileShaderData["textures"].items():
                if name in shaderData["textures"]:
                    boolValue = True
                    value = shaderData["textures"][name]
                else:
                    boolValue = False
                dynamicGUIDict.update({
                        name+"Bool": bpy.props.BoolProperty(default= boolValue),
                        name: bpy.props.StringProperty(default= value)
                        })
            textClss = type('I3D_UIShaderTextures', (bpy.types.PropertyGroup,), {'__annotations__': dynamicGUIDict})
            bpy.utils.register_class(textClss)      #set new gui elements
            bpy.types.Scene.I3D_UIShaderTextures = bpy.props.PointerProperty(type=textClss)
            g_dynamicGUIClsDict["parameters"] = paramClss
            g_dynamicGUIClsDict["textures"] = textClss

            # Parameter templates.
            for parameterTemplateId, parameterTemplate in fileShaderData["parameterTemplates"].items():
                dynamicGUIDict = {}

                clssName = 'I3D_UITemplateParameters_'+parameterTemplateId
                if bpy.context.scene.get(clssName):
                    del bpy.context.scene[clssName]
                try:
                    delattr(bpy.types.Scene, clssName)
                except:
                    pass

                parameterTemplatesToHandle = {subtemplateId: {'isCustom': False, 'value': 'None'} for subtemplateId, subtemplate in parameterTemplate["subtemplates"].items()}
                paramsToHandle = [paramName for paramName, _ in parameterTemplate["parameters"].items()]
                texturesToHandle = [textureName for textureName, _ in parameterTemplate["textures"].items()]

                paramValues = {paramName: {'isCustom': False, 'value': param} for paramName, param in parameterTemplate["parameters"].items()}
                textureValues = {textureName: {'isCustom': False, 'value': texture} for textureName, texture in parameterTemplate["textures"].items()}

                # First, handle parameters and textures which have a custom value set.
                handledParams = []
                for paramName in paramsToHandle:
                    if paramName not in shaderData["parameters"]:
                        continue

                    handledParams.append(paramName)

                    templatedParameterTemplateMenuName = "templatedParameterTemplateMenu_" + parameterTemplateId + "_" + paramName
                    if templatedParameterTemplateMenuName in materialObj:
                        templatedParameterTemplate = materialObj[templatedParameterTemplateMenuName]
                        try:
                            value = parameterTemplate["subtemplates"][parameterTemplate["rootSubTemplateId"]]["templates"][templatedParameterTemplate][paramName]
                        except:
                            value = shaderData["parameters"][paramName]
                    else:                        
                        value = shaderData["parameters"][paramName]

                    paramValues[paramName]["isCustom"] = True
                    paramValues[paramName]["value"] = value
                paramsToHandle = [paramName for paramName in paramsToHandle if paramName not in handledParams]

                handledTextures = []
                for textureName in texturesToHandle:
                    if textureName not in shaderData["textures"]:
                        continue

                    handledTextures.append(textureName)

                    value = shaderData["textures"][textureName]

                    textureValues[textureName]["isCustom"] = True
                    textureValues[textureName]["value"] = value
                texturesToHandle = [textureName for textureName in texturesToHandle if textureName not in handledTextures]
                    
                subTemplateId = parameterTemplate["rootSubTemplateId"]
                while subTemplateId is not None:
                    subTemplate = parameterTemplate["subtemplates"][subTemplateId]
                    parentSubTemplateId = subTemplate["parentId"]

                    boolValue = False
                    selectedTemplateId = parameterTemplatesToHandle[subTemplateId]["value"]

                    try:
                        boolValue = subTemplateId in shaderData["parameterTemplates"][parameterTemplateId]
                        if boolValue:
                            selectedTemplateId = shaderData["parameterTemplates"][parameterTemplateId][subTemplateId]
                    except KeyError:
                        pass

                    parameterTemplatesToHandle[subTemplateId]["isCustom"] = boolValue
                    parameterTemplatesToHandle[subTemplateId]["value"] = selectedTemplateId

                    parentSubTemplate = "None"

                    # Get selected template
                    selectedTemplate = None
                    if selectedTemplateId in subTemplate["templates"]:
                        selectedTemplate = subTemplate["templates"][selectedTemplateId]

                        # Handle parameters and textures set by this subtemplate
                        handledParams = []
                        for paramName in paramsToHandle:
                            if paramName not in selectedTemplate:
                                continue

                            handledParams.append(paramName)

                            value = selectedTemplate[paramName]

                            paramValues[paramName]["isCustom"] = False
                            paramValues[paramName]["value"] = value

                        paramsToHandle = [paramName for paramName in paramsToHandle if paramName not in handledParams]

                        handledTextures = []
                        for textureName in texturesToHandle:
                            if textureName not in selectedTemplate:
                                continue

                            handledTextures.append(textureName)

                            value = selectedTemplate[textureName]

                            textureValues[textureName]["isCustom"] = False
                            textureValues[textureName]["value"] = value
                        texturesToHandle = [textureName for textureName in texturesToHandle if textureName not in handledTextures]

                        # Find which parent sub template should be used if its not set.
                        if "parentTemplate" in selectedTemplate:
                            parentSubTemplate = selectedTemplate["parentTemplate"]
                        else:
                            parentSubTemplate = subTemplate["defaultParentTemplate"]

                    if parentSubTemplateId is not None:
                        parameterTemplatesToHandle[parentSubTemplateId]["value"] = parentSubTemplate

                    enums = [(templateName, templateName, '') for templateName, _ in subTemplate["templates"].items()]
                    enums.insert(0, ("None", "None", ""))
                    dynamicGUIDict.update({
                        subTemplateId + "Bool": bpy.props.BoolProperty(name = subTemplateId + "Bool", default = boolValue, update = parameterTemplateSelectedCallback(parameterTemplateId, subTemplateId)),
                        subTemplateId + "_Template": bpy.props.EnumProperty(name = subTemplate["name"], items=enums, update = parameterTemplateSelectedCallback(parameterTemplateId, subTemplateId), default = selectedTemplateId)
                    })
                    
                    subTemplateId = subTemplate["parentId"]

                rootSubTemplateId = parameterTemplate["rootSubTemplateId"]
                rootTemplates = [("None", "None", "")]
                rootTemplates = rootTemplates + [(templateName, templateName, "") for templateName, _ in parameterTemplate["subtemplates"][rootSubTemplateId]["templates"].items()]
                for paramName, param in paramValues.items():
                    value = param["value"]

                    try:
                        valueList = [float(x) for x in value.strip().split(" ")]
                    except Exception as e:
                        #print(e)
                        valueList = []
                    valueList = valueList + [1.0,1.0,1.0,1.0]

                    dynamicGUIDict.update({
                        paramName+"Bool": bpy.props.BoolProperty(name = paramName+"Bool", default=param["isCustom"], update = templatedParameterEnableCallback(parameterTemplateId, rootSubTemplateId, paramName)),
                        paramName+"_0": bpy.props.FloatProperty(default = valueList[0], precision = dcc.FLOAT_PRECISION, update = templatedParameterUpdateCallback(parameterTemplateId, rootSubTemplateId, paramName)),
                        paramName+"_1": bpy.props.FloatProperty(default = valueList[1], precision = dcc.FLOAT_PRECISION, update = templatedParameterUpdateCallback(parameterTemplateId, rootSubTemplateId, paramName)),
                        paramName+"_2": bpy.props.FloatProperty(default = valueList[2], precision = dcc.FLOAT_PRECISION, update = templatedParameterUpdateCallback(parameterTemplateId, rootSubTemplateId, paramName)),
                        paramName+"_3": bpy.props.FloatProperty(default = valueList[3], precision = dcc.FLOAT_PRECISION, update = templatedParameterUpdateCallback(parameterTemplateId, rootSubTemplateId, paramName)),
                        "templatedParameterTemplateMenu_" + parameterTemplateId + "_" + paramName: bpy.props.EnumProperty(items = rootTemplates, update = templateForParameterSelectedCallback(parameterTemplateId, rootSubTemplateId, paramName), default = materialObj["templatedParameterTemplateMenu_" + parameterTemplateId + "_" + paramName] if "templatedParameterTemplateMenu_" + parameterTemplateId + "_" + paramName in materialObj else "None")
                    })
                    
                for textureName, texture in textureValues.items():
                    dynamicGUIDict.update({
                            textureName+"Bool": bpy.props.BoolProperty(name=textureName, default=texture["isCustom"]),
                            textureName: bpy.props.StringProperty(default=texture["value"])
                            })
                    
                templateParameterClss = type(clssName, (bpy.types.PropertyGroup,), {'__annotations__': dynamicGUIDict})
                bpy.utils.register_class(templateParameterClss)
                
                try:
                    setattr(bpy.types.Scene, clssName, bpy.props.PointerProperty(type=templateParameterClss))
                except Exception as e:
                    print("Could not add class {} to scene".format(clssName))
                    print(e)
                    continue
                else:
                    g_dynamicGUIClsDict[parameterTemplateId] = templateParameterClss

            if materialObj is not None:
                if "shadingRate" in materialObj:
                    context.scene.I3D_UIexportSettings.I3D_shadingRate = materialObj["shadingRate"]
                else:
                    context.scene.I3D_UIexportSettings.I3D_shadingRate = "1x1"

                if "materialSlotName" in materialObj:
                    context.scene.I3D_UIexportSettings.I3D_materialSlotName = materialObj["materialSlotName"]
                else:
                    context.scene.I3D_UIexportSettings.I3D_materialSlotName = ""

                if materialObj.blend_method == 'BLEND':
                    context.scene.I3D_UIexportSettings.I3D_alphaBlending = True
                else:
                    context.scene.I3D_UIexportSettings.I3D_alphaBlending = False

                if "alphaBlending" in materialObj:
                    context.scene.I3D_UIexportSettings.I3D_alphaBlending = True
                else:
                    context.scene.I3D_UIexportSettings.I3D_alphaBlending = False
            try:
                context.scene.I3D_UIexportSettings.I3D_shaderVariationEnum = shaderVariation
            except:
                print("Variation not existing in loaded file")
                return {'FINISHED'}
        return {'FINISHED'}

class I3D_OT_PanelAddShader_ButtonAdd( bpy.types.Operator):
    """ GUI element Button to Add custom Shader settings from the Exporter GUI into blender"""

    bl_idname= "i3d.paneladdshader_buttonadd"
    bl_label = "Add Shader"

    def execute(self,context):
        """ Creates and registers dynamic classes for dynamic GUI elements """
        # try:
        #     actObjName = context.active_object.name
        # except:
        #     try:
        #         actObjName = dccBlender.getSelectedNodes()[0]
        #     except:
        #         actObjName = bpy.data.scenes[context.scene.name].I3D_UIexportSettings.UI_PrevActiveObjectName
        # activeObject = bpy.data.objects[actObjName]
        # materialObj = activeObject.active_material
        # if materialObj == None:
        #     self.report({'WARNING'},"Cannot Add Shader")
        #     if context.active_object == None:
        #         self.report({'WARNING'},"No Object is Selected")
        #         return {'CANCELLED'}
        #     else:
        #         self.report({'WARNING'},"{} has no Material".format(context.active_object.name))
        #         return {'CANCELLED'}

        materialObjName = bpy.context.scene.I3D_UIexportSettings.I3D_selectedMaterialEnum
        materialObj = None
        if materialObjName != "None":
            materialObj = bpy.data.materials[materialObjName]

        if materialObj == None:
            self.report({'WARNING'},"Cannot Add Shader, no material is selected")
            return {'CANCELLED'}

        for delKey in [k for k in materialObj.keys() if k.startswith("custom")]:
            del materialObj[delKey]
        if materialObj:
            dirPath = bpy.path.abspath(context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation)
            dirPath = dirPath.replace("$", bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation)
            fileName = context.scene.I3D_UIexportSettings.I3D_shaderEnum
            if fileName == "None":
                self.report({'WARNING'},'No config xml file set!')
                return {'FINISHED'}
            xmlFilePath = dirPath + os.sep + fileName
            if not os.path.isfile(xmlFilePath):
                self.report({'WARNING'},'Could not find xml file! (%s)' % xmlFilePath)
                return {'FINISHED'}
            if not xmlFilePath.endswith(".xml"):
                self.report({'WARNING'},"Selected File is not xml format: {}".format(xmlFilePath.split("\\")[-1]))
                return {'FINISHED'}

            if context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation[0] == "$":
                xmlFilePath = context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation + os.sep + fileName
            else:
                xmlFilePath = pathUtil.resolvePath(xmlFilePath,targetDirectory = bpy.path.abspath("//"))
            materialObj["customShader"] = xmlFilePath
            if "parameters" in g_dynamicGUIClsDict:
                for k,i in g_dynamicGUIClsDict["parameters"].__annotations__.items():
                    try:
                        i = i.keywords
                    except:
                        i = i[1]
                    if k.endswith("Bool"):
                        if (k in context.scene.I3D_UIShaderParameters and context.scene.I3D_UIShaderParameters[k]) or (i['default'] and not k in context.scene.I3D_UIShaderParameters):      #default test, since default values are not accesable from the API
                            name = "customParameter_"+k[:-4]        #add prefix customParameter_ and remove "Bool" postfix
                            postfix = ['_0','_1','_2','_3']
                            value = ''
                            for postf in postfix:
                                postf_key = k[:-4]+postf
                                if postf_key in context.scene.I3D_UIShaderParameters:
                                    value = value + str(bpy.context.scene.I3D_UIShaderParameters[postf_key]) + " "
                                else:
                                    try:
                                        value = value + str(g_dynamicGUIClsDict["parameters"].__annotations__[postf_key].keywords['default']) + " "
                                    except:
                                        value = value + str(g_dynamicGUIClsDict["parameters"].__annotations__[postf_key][1]['default']) + " "
                            value = value.strip()
                            #legacy check
                            if k[:-4] in context.scene.I3D_UIShaderParameters and value == '':
                                value = bpy.context.scene.I3D_UIShaderParameters[k[:-4]]
                            elif value == '':
                                try:
                                    value = g_dynamicGUIClsDict["parameters"].__annotations__[k[:-4]].keywords['default']
                                except:
                                    value = g_dynamicGUIClsDict["parameters"].__annotations__[k[:-4]][1]['default']
                            materialObj[name] = value

            if "textures" in g_dynamicGUIClsDict:
                for k,i in g_dynamicGUIClsDict["textures"].__annotations__.items():
                    try:
                        i = i.keywords
                    except:
                        i = i[1]
                    if k.endswith("Bool"):
                        if (k in context.scene.I3D_UIShaderTextures and context.scene.I3D_UIShaderTextures[k]) or (i['default'] and not k in context.scene.I3D_UIShaderTextures):
                            name = "customTexture_"+k[:-4]        #add prefix customParameter_ and remove "Bool" postfix
                            if k[:-4] in context.scene.I3D_UIShaderTextures:
                                value = bpy.context.scene.I3D_UIShaderTextures[k[:-4]]
                            else:
                                try:
                                    value = g_dynamicGUIClsDict["textures"].__annotations__[k[:-4]].keywords['default']
                                except:
                                    value = g_dynamicGUIClsDict["textures"].__annotations__[k[:-4]][1]['default']
                            materialObj[name] = value

            for dynamicGUIClsName, dynamicGUICls in g_dynamicGUIClsDict.items():
                # Skip textures and parameters entries, otherwise we assume that its a template parameter
                if dynamicGUIClsName == "textures" or dynamicGUIClsName == "parameters":
                    continue

                clssName = 'I3D_UITemplateParameters_'+dynamicGUIClsName
                try:
                    dataClass = getattr(context.scene, clssName)
                except Exception as exception:
                    # TODO(jdellsperger): Warning / Error
                    continue
                else:
                    # Differentiate types of parameters by their ending string:
                    # Bool: Checkbox whether the parameter is enabled or not
                    # _0 to _3: Regular parameter (float4)
                    # _Template: Template parameter (string/enum)
                    # Starts with templatedParameterTemplateMenu_: Template for specific parameter (enum)
                    # Otherwise: Texture parameter (string)

                    for k, v in dynamicGUICls.__annotations__.items():
                        if not k.endswith("Bool"):
                            continue

                        if not getattr(dataClass, k):
                            # Custom parameter is not enabled, skip
                            # TODO(jdellsperger): Remove stored attribute on material if any
                            continue

                        paramName = k[:-4] # Remove trailing "Bool"
                        prefix = ""
                        value = ""
                        if hasattr(dataClass, paramName + "_0") and \
                           hasattr(dataClass, paramName + "_1") and \
                           hasattr(dataClass, paramName + "_2") and \
                           hasattr(dataClass, paramName + "_3"):
                            # Is a regular parameter
                            prefix = "customParameter_"
                            value = \
                                str(getattr(dataClass, paramName + "_0")) + " " + \
                                str(getattr(dataClass, paramName + "_1")) + " " + \
                                str(getattr(dataClass, paramName + "_2")) + " " + \
                                str(getattr(dataClass, paramName + "_3"))
                        elif hasattr(dataClass, paramName + "_Template"):
                            # Parameter template
                            prefix = "customParameterTemplate_" + dynamicGUIClsName + "_"
                            value = getattr(dataClass, paramName + "_Template")
                        elif hasattr(dataClass, paramName):
                            # Texture
                            prefix = "customTexture_"
                            value = getattr(dataClass, paramName)
                        else:
                            # Invalid parameter
                            self.report({"ERROR"}, "Invalid parameter '{}' encountered".format(paramName))
                            continue

                        # Store specific template selected for this parameter, if any.
                        parameterTemplateName = "templatedParameterTemplateMenu_" + dynamicGUIClsName + "_" + paramName
                        try:
                            selectedParameterTemplate = getattr(dataClass, parameterTemplateName)
                            if selectedParameterTemplate == "None":
                                del(materialObj[parameterTemplateName])
                            else:
                                materialObj[parameterTemplateName] = selectedParameterTemplate
                        except Exception as e:
                            # no selected parameter.
                            pass

                        materialObj[prefix + paramName] = value

            if context.scene.I3D_UIexportSettings.I3D_shaderVariationEnum != "None":
                materialObj["customShaderVariation"] = context.scene.I3D_UIexportSettings.I3D_shaderVariationEnum
            else:
                try:
                    del materialObj["customShaderVariation"]
                except:
                    pass

            if context.scene.I3D_UIexportSettings.I3D_shadingRate != "":
                materialObj["shadingRate"] = context.scene.I3D_UIexportSettings.I3D_shadingRate
            elif "shadingRate" in materialObj:
                del(materialObj["shadingRate"])

            

            if context.scene.I3D_UIexportSettings.I3D_materialSlotName != "":
                materialObj["materialSlotName"] = context.scene.I3D_UIexportSettings.I3D_materialSlotName
            elif "materialSlotName" in materialObj:
                del(materialObj["materialSlotName"])

        return {'FINISHED'}

class I3D_OT_PanelExport_ButtonClose( bpy.types.Operator ):
    """ GUI element Buttom to close GIANTS I3D Exporter"""

    bl_idname  = "i3d.panelexport_buttonclose"
    bl_label   = "Close"

    def execute( self, context ):
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
        return {'FINISHED'}

class I3D_OT_PanelXMLidentification_ButtonAdd( bpy.types.Operator):
    """ GUI element Button to set Node Id for XML configuration to object name """

    bl_idname= "i3d.panelxmlidentification_buttonadd"
    bl_label = "XML Id"
    bl_description = "Sets Node Id to the default value, the Node Name"
    state : bpy.props.StringProperty()

    def execute(self,context):

        actObjName = bpy.data.scenes[context.scene.name].I3D_UIexportSettings.UI_ActiveObjectName
        actObjName = dccBlender.getFormattedNodeName(actObjName)
        context.scene.I3D_UIexportSettings.I3D_XMLConfigIdentification = actObjName
        return {'FINISHED'}

class I3D_OT_PanelOpenXMLFilebrowser(bpy.types.Operator,bpy_extras.io_utils.ImportHelper):
    """ GUI element Button to open a Filebrowser with *.xml filter applied"""

    bl_idname = "i3d.openxmlfilebrowser"
    bl_label = "select XML"
    filter_glob: bpy.props.StringProperty( default='*.xml', options={'HIDDEN'} )

    def execute(self, context):
        filename, extension = os.path.splitext(self.filepath)
        path = filename + extension
        if not os.path.isfile(path):
            self.report({'WARNING'},"{} is no valid xml file".format(path))
            return {'CANCELLED'}
        abspath = bpy.path.abspath(path) #bpy.path.relpath(path)
        if abspath not in context.scene.I3D_UIexportSettings.I3D_updateXMLFilePath:
            context.scene.I3D_UIexportSettings.I3D_updateXMLFilePath = context.scene.I3D_UIexportSettings.I3D_updateXMLFilePath +";{};;".format(abspath)
        return {'FINISHED'}

class I3D_OT_PanelOpenFolderFilebrowser(bpy.types.Operator,bpy_extras.io_utils.ImportHelper):
    """ GUI element Button to select a Folder Path """

    bl_idname = "i3d.openfolderfilebrowser"
    bl_label = "select Folder"
    bl_description = "Search and select Folder Path"
    state      : bpy.props.IntProperty()

    def execute(self, context):
        filename, extension = os.path.splitext(self.filepath)
        if self.state == 1: # Game location
            path = filename.rsplit("\\",1)[0] + "\\" #remove filename and extension
            abspath = bpy.path.abspath(path)
            context.scene.I3D_UIexportSettings.I3D_gameLocationDisplay = abspath

        elif self.state == 2: # Shaders
            path = filename.rsplit("\\",1)[0] + "\\"    #remove filename and extension
            context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation = path
            updateShaderFolderLocation(context)
            if not context.scene.I3D_UIexportSettings.I3D_shaderEnum in [t[0] for t in I3D_PT_PanelExport.getShadersFromDirectory(self,context)]:
                context.scene.I3D_UIexportSettings.I3D_shaderEnum = [t[0] for t in I3D_PT_PanelExport.getShadersFromDirectory(self,context)][0]
            shaderEnumUpdate(self,context)

        return {'FINISHED'}

class I3D_OT_PanelRefreshGamePath(bpy.types.Operator):
    """ GUI element Button to auto search and update the game installation path only available on Windows """

    bl_idname = "i3d.panelrefreshgamepath"
    bl_label = "refresh game path"
    bl_description = "Search automatically for a Game Installation and updates Game Location Path"

    def execute(self, context):
        # context.scene.I3D_UIexportSettings.I3D_gameLocation = ""
        context.scene.I3D_UIexportSettings.I3D_gameLocationDisplay = dirf.findFS22Path()
        return {'FINISHED'}

class I3D_OT_PanelSetGameShader(bpy.types.Operator):
    """ GUI element Button to auto search and set the shader to the game shader location only available on Windows """

    bl_idname = "i3d.panelsetgameshader"
    bl_label = "Detect Path"
    bl_description = "Search automatically for the shader folder in the Game Installation"

    def execute(self, context):
        gameInstallationPath = context.scene.I3D_UIexportSettings.I3D_gameLocation
        if gameInstallationPath == "":
            gameInstallationPath = dirf.findFS22Path()
            if gameInstallationPath == "":
                self.report({'WARNING'},"No Game Installation found")
                return {'FINISHED'}

        self.report({'INFO'},"Game Shader Path set")
        gameShaderFolder = gameInstallationPath + "data\\shaders\\"
        if not os.path.isdir(bpy.path.abspath(gameShaderFolder)):
            self.report({'WARNING'},"{} is no valid path".format(gameShaderFolder))
            return {'FINISHED'}

        context.scene.I3D_UIexportSettings.I3D_shaderFolderLocation = gameInstallationPath + "data\\shaders\\"
        shaderEnumUpdate(self,context)
        return {'FINISHED'}

class I3D_OT_PanelOpenI3DFilebrowser(bpy.types.Operator,bpy_extras.io_utils.ImportHelper):
    """ GUI element Button to open a Filebrowser with *.i3d filter applied"""

    bl_idname = "i3d.openi3dfilebrowser"
    bl_label = "Set i3d File"
    filter_glob: bpy.props.StringProperty( default='*.i3d', options={'HIDDEN'} )

    def execute(self, context):
        filename, extension = os.path.splitext(self.filepath)
        if extension != ".i3d":
            self.report({'WARNING'},"Changed File Location extension from {} to '.i3d'".format(extension))
            extension = ".i3d"
        path = filename + extension
        try:
            relpath = bpy.path.relpath(path)
        except:
            relpath = path
        context.scene.I3D_UIexportSettings.I3D_exportFileLocation = relpath
        return {'FINISHED'}

class I3D_OT_PanelOpenDDSFilebrowser(bpy.types.Operator,bpy_extras.io_utils.ImportHelper):
    """ GUI element Button to open a Filebrowser with *.dds filter applied"""

    bl_idname = "i3d.openddsfilebrowser"
    bl_label = "Set dds File"
    filter_glob: bpy.props.StringProperty( default='*.dds', options={'HIDDEN'} )

    def execute(self, context):
        filename, extension = os.path.splitext(self.filepath)
        if extension != ".dds":
            self.report({'WARNING'},"Changed File Location extension from {} to '.dds'".format(extension))
            extension = ".dds"
        path = filename + extension
        try:
            relpath = bpy.path.relpath(path)
        except:
            relpath = path
        context.scene.I3D_UIexportSettings.I3D_objectDataFilePath = relpath
        return {'FINISHED'}
    
class I3D_OT_PanelOpenIESFilebrowser(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """ GUI element Button to open a Filebrowser with *.ies filter applied"""

    bl_idname = "i3d.openiesfilebrowser"
    bl_label = "Set ies File"
    filter_glob: bpy.props.StringProperty( default='*.ies', options={'HIDDEN'} )

    def execute(self, context):
        filename, extension = os.path.splitext(self.filepath)
        if extension != ".ies":
            self.report({'WARNING'},"Changed File Location extension from {} to '.ies'".format(extension))
            extension = ".ies"
        path = filename + extension
        #try:
        #    relpath = bpy.path.abspath(path)
        #except:
        #    relpath = path
        #context.scene.I3D_UIexportSettings.I3D_iesProfileFile = relpath
        context.scene.I3D_UIexportSettings.I3D_iesProfileFile = path
        return {'FINISHED'}

class I3D_OT_PanelTools_Button( bpy.types.Operator ):
    """ Multi purpose GUI Button element for Tools tab"""

    bl_idname  = "i3d.paneltools_button"
    bl_label   = ""
    state      : bpy.props.IntProperty()

    def execute( self, context ):

        # bpy.ops.wm.console_toggle() #DEBUG command
        try:
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set ( mode = 'OBJECT' ) #export in object mode
        except:
            current_mode = 'OBJECT'

        if   1 == self.state:  #export dds
            i3d_export.I3DExportDDS()

        try:
            bpy.ops.object.mode_set ( mode = current_mode )
        except:
            pass
        #Info Log output
        for header in logUtil.ActionLog.header:
            self.report(header[0],header[1])
        for message in logUtil.ActionLog.message:
            self.report(message[0],message[1])
        logUtil.ActionLog.reset()
        return {'FINISHED'}
    
class I3D_OT_PanelMaterial_OpenMaterialTemplatesWindowButton(bpy.types.Operator):
    """ GUI element Button to open the material library """

    bl_idname = "i3d.openmaterialtemplateswindow"
    bl_label = "Material Templates"
    bl_description = "Opens a preview window of reusable material templates."
    
    # State to track whether the material templates window is open or not.
    state      : bpy.props.IntProperty(name = "State", default = 0)

    def execute(self, context):
        #self.report({'INFO'}, 'I3D_OT_PanelMaterial_OpenMaterialTemplatesWindowButton::execute()')
        if self.state == 0:
            try:
                global g_loadedMaterialTemplates

                try:
                    materialTemplateFilename = "$data/shared/detailLibrary/materialTemplates.xml"
                    templatesXmlFilename = materialTemplateFilename.replace("$", bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation)
                    xmlTree = xml_ET.parse(templatesXmlFilename)
                except xml_ET.ParseError as err:
                    self.report({"INFO"}, "Failed to load parameter templates from '%s': %s" % (templatesXmlFilename, err))
                    return {'CANCELLED'}
                else:
                    # TODO(jdellsperger): Make xml file actually selectable
                    context.scene.I3D_UIMaterialTemplateProperties.fileLocation = materialTemplateFilename
                    templatesFileRoot = xmlTree.getroot()
                    for template in templatesFileRoot.findall("template"):
                        iconFilename = template.get("iconFilename")
                        iconFilenamePath = iconFilename.replace("$", bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation)
                        name = template.get("name")
                        categoryString = template.get("category")
                        categories = categoryString.split("/")

                        templateAttributesDict = {}
                        templateAttributes = template.attrib

                        # Delete meta attributes
                        del templateAttributes["name"]
                        del templateAttributes["category"]
                        del templateAttributes["iconFilename"]

                        for templateAttribute in templateAttributes:
                            templateAttributesDict[templateAttribute] = template.get(templateAttribute)

                        categoryDict = g_loadedMaterialTemplates
                        categoryString = ""
                        for category in categories:
                            categoryString = categoryString + category
                            if not category in categoryDict:
                                categoryDict[category] = {'expanded': False, "thumbnails": None}
                                categoryDict[category]["thumbnails"] = bpy.utils.previews.new()
                            categoryDict = categoryDict[category]
                            categoryString = categoryString + "_"

                        g_loadedMaterialTemplates['templates'][name] = templateAttributesDict
                        if name not in categoryDict["thumbnails"]:
                            categoryDict["thumbnails"].load(name, iconFilenamePath, "IMAGE")
                
                bpy.utils.register_class(I3D_PT_MaterialTemplates)
                self.state = 1
            except Exception as e:
                self.report({'INFO'}, 'I3D_OT_PanelMaterial_OpenMaterialTemplatesWindowButton::execute::cancelled1')
                return {'CANCELLED'}
        elif self.state == 1:
            #TODO(jdellsperger): Should we unload everything (including thumbnails) in case of close?

            try:
                bpy.utils.unregister_class(I3D_PT_MaterialTemplates)
                self.state = 0
            except:
                self.report({'INFO'}, 'I3D_OT_PanelMaterial_OpenMaterialTemplatesWindowButton::execute::cancelled2')
                return {'CANCELLED'}
        return {'FINISHED'}
    
class I3D_OT_PanelMaterial_ApplyMaterialTemplateToSelection(bpy.types.Operator):
    """Event triggered when a material template preview was clicked."""

    bl_idname = "i3d.apply_material_template_to_selection"
    bl_label = "Apply to Selection"
    bl_description = "Creates a new material from the template parameters and assigns it to the selected object."
    
    templateName : bpy.props.StringProperty()

    def execute(self, context):
        # TODO(jdellsperger): Assign material to entire object or to faces, depending on mode
        mat = bpy.data.materials.new(self.templateName + "Mat")
        mat["customShader"] = "$data/shaders/vehicleShader.xml"
        mat["customParameterTemplate_brandColor_material"] = self.templateName

        # Assign material to active object
        obj = bpy.context.object
        obj.data.materials.append(mat)

        # self.report({'INFO'}, "template clicked: {}".format(self.templateName))
        return {'FINISHED'}
    
class I3D_OT_PanelMaterial_UseMaterialNameAsSlotNameButton(bpy.types.Operator):
    """ GUI element Button to copy the selected material name to the slot name text input """

    bl_idname = "i3d.usematerialnameasslotname"
    bl_label = "Use Material Name"
    bl_description = "Copies the name of the currently selected material to the slot name text input."
    
    def execute(self, context):
        try:
            context.scene.I3D_UIexportSettings.I3D_materialSlotName = context.object.active_material.name
        except:
            return {'CANCELLED'}
        return {'FINISHED'}
    
#-------------------------------------------------------------------------------
#   Init Scene PropertyGroups
#-------------------------------------------------------------------------------

class I3D_UIexportSettings( bpy.types.PropertyGroup ):
    """ Definition of all static GUI element properties """

    I3D_collisionFilterGroup  : bpy.props.IntProperty( name = "Collision Filter Group", default = dcc.SETTINGS_ATTRIBUTES['I3D_collisionFilterGroup']['defaultValue'] )
    I3D_collisionFilterMask   : bpy.props.IntProperty( name = "Collision Filter Mask",  default = dcc.SETTINGS_ATTRIBUTES['I3D_collisionFilterMask']['defaultValue'] )
    I3D_collisionFilterPreset : bpy.props.EnumProperty(
                                items = g_collisionFiltersData.presetsEnum,
                                name="Collision Preset",
                                default="-",
                                update=updateCollisionFilters
                            )

    I3D_XMLConfigExport : bpy.props.BoolProperty (name = "", description = "Export to config. XML if checked", default = False, update=I3D_PT_PanelExport.updateXMLconfigBool)
    I3D_XMLConfigIdentification : bpy.props.StringProperty (name = "Node Id", description = "XML config. i3dMapping identification", update=I3D_PT_PanelExport.updateXMLconfigId)
    UI_settingsMode : bpy.props.EnumProperty(
                items = [ ('exp' ,  'Export'   ,  ''),
                          ('attr',  'Attributes', ''),
                          ('tools',  'Tools', ''),
                          ('shader',  'Material', ''),
                          ('newMaterial',  'New Material', ''),
                          ('shapeAttribute',  'Shape Export Attrib', '')
                          ],
                name = "Settings Mode"
                )
    UI_exportOptions        : bpy.props.BoolProperty   ( name = "Export Options",        default = True )
    UI_shapeExportSubparts  : bpy.props.BoolProperty   ( name = "Shape Export Subparts", default = True )
    UI_miscellaneous        : bpy.props.BoolProperty   ( name = "Miscellaneous",         default = True )
    UI_MeshProcessing        : bpy.props.BoolProperty  ( name = "Mesh Processing",       default = True )
    UI_gameLocation         : bpy.props.BoolProperty   ( name = "Game Location",         default = False )
    UI_xmlConfig            : bpy.props.BoolProperty   ( name = "XML config File",       default = True )
    UI_outputFile           : bpy.props.BoolProperty   ( name = "Output File",           default = True )
    UI_currentNode          : bpy.props.BoolProperty   ( name = "Current Node",          default = True )
    UI_predefined           : bpy.props.BoolProperty   ( name = "Predefined",            default = False )
    UI_rigidBody            : bpy.props.BoolProperty   ( name = "Rigid Body",            default = False )
    UI_joint                : bpy.props.BoolProperty   ( name = "Joint",                 default = False )
    UI_rendering            : bpy.props.BoolProperty   ( name = "Rendering",             default = False )
    UI_environment          : bpy.props.BoolProperty   ( name = "Environment",           default = False )
    UI_objectDataTexture    : bpy.props.BoolProperty   ( name = "Object Data Texture",   default = False )
    UI_showLightAttributes  : bpy.props.BoolProperty   ( name = "Show Light Attributes", default = False )
    UI_lightAttributes      : bpy.props.BoolProperty   ( name = "Light Attributes",      default = False )
    UI_ddsExportOptions     : bpy.props.BoolProperty   ( name = "DDS Export Options",    default = False )
    UI_shaderFolder         : bpy.props.BoolProperty   ( name = "Shaders Folder",        default = True )
    UI_customTools          : bpy.props.BoolProperty   ( name = "Custom Tools",          default = True )
    UI_ActiveObjectName     : bpy.props.StringProperty ( name = "Active Object Name", default = "empty")
    UI_PrevActiveObjectName : bpy.props.StringProperty ( name = "Previously Active Object Name", default = "empty" """, update=test""")
    UI_autoAssign           : bpy.props.BoolProperty   ( name = "Auto Assign", default = False, description = "Update attributes automatic to selected object",update = toggleAutoAssign)

    UI_lightUseShadow       : bpy.props.BoolProperty   ( name = "Use Shadow", default = False, update = lightUseShadowUpdate )

    UI_materialTools   : bpy.props.BoolProperty ( name = "Tools", default = True)

    # I3D_exportIK                  : bpy.props.BoolProperty   ( name = "IK",                   default = dcc.SETTINGS_UI['I3D_exportIK']['defaultValue'] )
    I3D_exportAnimation           : bpy.props.BoolProperty   ( name = "Animation", description="Export Animation Data",            default = dcc.SETTINGS_UI['I3D_exportAnimation']['defaultValue']  )
    I3D_exportShapes              : bpy.props.BoolProperty   ( name = "Shapes", description="Export Shapes as Transform Groups if unchecked", default = dcc.SETTINGS_UI['I3D_exportShapes']['defaultValue']  )
    I3D_exportNurbsCurves         : bpy.props.BoolProperty   ( name = "Nurbs Curves",description="Export Nurbs Curves as Transform Groups if unchecked",         default = dcc.SETTINGS_UI['I3D_exportNurbsCurves']['defaultValue'] )
    I3D_exportLights              : bpy.props.BoolProperty   ( name = "Lights", description="Export Lights as Transform Groups if unchecked",              default = dcc.SETTINGS_UI['I3D_exportLights']['defaultValue']  )
    I3D_exportCameras             : bpy.props.BoolProperty   ( name = "Cameras",description="Export Cameras as Transform Groups if unchecked",              default = dcc.SETTINGS_UI['I3D_exportCameras']['defaultValue']  )
    I3D_binaryFiles             : bpy.props.BoolProperty   ( name = "Binary Files",description="Export i3d in binary format",              default = dcc.SETTINGS_UI['I3D_binaryFiles']['defaultValue']  )

    # I3D_exportParticleSystems     : bpy.props.BoolProperty   ( name = "Particle Systems",     default = dcc.SETTINGS_UI['I3D_exportParticleSystems']['defaultValue'] )
    I3D_exportUserAttributes      : bpy.props.BoolProperty   ( name = "User Attributes",description="Export User Attributes if checked",       default = dcc.SETTINGS_UI['I3D_exportUserAttributes']['defaultValue']  )
    I3D_export32bitposition             : bpy.props.BoolProperty   ( name = "Export32bitposition",description="Export 32 bit if checked",              default = dcc.SETTINGS_UI['I3D_export32bitposition']['defaultValue']  )
    I3D_exportNormals             : bpy.props.BoolProperty   ( name = "Normals",description="Export Normals if checked",              default = dcc.SETTINGS_UI['I3D_exportNormals']['defaultValue']  )
    I3D_use32bitQT                : bpy.props.BoolProperty   ( name = "I3D_use32bitQT",description="Export normals using higher QT",              default = dcc.SETTINGS_UI['I3D_use32bitQT']['defaultValue']  )
    I3D_exportTangents            : bpy.props.BoolProperty   ( name = "Tangents",description="Export Tangents if checked",              default = dcc.SETTINGS_UI['I3D_exportTangents']['defaultValue']  )
    I3D_exportTangentsBinaryRecalc : bpy.props.BoolProperty   ( name = "TangentsBinaryRecalc",description="Binary Recalculate Tangents if checked",              default = dcc.SETTINGS_UI['I3D_exportTangentsBinaryRecalc']['defaultValue']  )
    I3D_exportColors              : bpy.props.BoolProperty   ( name = "Vertex Colors",description="Export Vertex Colors if checked",        default = dcc.SETTINGS_UI['I3D_exportColors']['defaultValue']  )
    I3D_exportTexCoords           : bpy.props.BoolProperty   ( name = "UVs",description="Export UV mapping if checked",                  default = dcc.SETTINGS_UI['I3D_exportTexCoords']['defaultValue']  )
    I3D_exportTexCoordsUVDensity  : bpy.props.BoolProperty   ( name = "UVs Density",description="Export UV mapping density if checked (alot faster off)", default = dcc.SETTINGS_UI['I3D_exportTexCoordsUVDensity']['defaultValue']  )
    
    
    I3D_exportSkinWeigths         : bpy.props.BoolProperty   ( name = "Skin Weigths",description="Export Bones and Skinning attributes if checked",         default = dcc.SETTINGS_UI['I3D_exportSkinWeigths']['defaultValue']  )
    I3D_exportMergeGroups         : bpy.props.BoolProperty   ( name = "Merge Groups", description="Export Merge Groups if checked",        default = dcc.SETTINGS_UI['I3D_exportMergeGroups']['defaultValue']  )
    I3D_exportVerbose             : bpy.props.BoolProperty   ( name         = "Verbose",
                                                               description  = "Print info to System Console",
                                                               default      = dcc.SETTINGS_UI['I3D_exportVerbose']['defaultValue'] )
    I3D_generateexporterprofile   : bpy.props.BoolProperty   ( name         = "Generate Profile of Export",
                                                               description  = "Gives a profile of the export",
                                                               default      = False )

    I3D_UImaxMeshSizeX             : bpy.props.FloatProperty   ( name         = "Max Size X",
                                                               description  = "If not Zero we will split the mesh up by size",
                                                               default      = dcc.SETTINGS_UI['I3D_UImaxMeshSizeX']['defaultValue'],  
                                                               min=0.0,
                                                               max=100.0,
                                                               step=1.0 )

    I3D_UImaxMeshSizeY             : bpy.props.FloatProperty   ( name         = "Max Size Y",
                                                               description  = "If not Zero we will split the mesh up by size",
                                                               default      = dcc.SETTINGS_UI['I3D_UImaxMeshSizeX']['defaultValue'],  
                                                               min=0.0,
                                                               max=100.0,
                                                               step=1.0 )

    I3D_UImaxMeshSizeZ             : bpy.props.FloatProperty   ( name         = "Max Size Z",
                                                               description  = "If not Zero we will split the mesh up by size",
                                                               default      = dcc.SETTINGS_UI['I3D_UImaxMeshSizeX']['defaultValue'],  
                                                               min=0.0,
                                                               max=100.0,
                                                               step=1.0 )


    I3D_UIexportCopyFiles         : bpy.props.BoolProperty   ( name = "Copy Files Relative to Blend File",description="Copies files over to the target i3d relative to where they are with the blender file",      default = dcc.SETTINGS_UI['I3D_UIexportCopyFiles']['defaultValue'])
    I3D_exportRelativePaths       : bpy.props.BoolProperty   ( name = "Export Relative Paths",description="Export File Paths relative to the *.i3d File",      default = dcc.SETTINGS_UI['I3D_exportRelativePaths']['defaultValue'])
    I3D_exportGameRelativePath    : bpy.props.BoolProperty   ( name = "Export Game Relative Path",description="Export File Paths relative to the Game Installation Path",       default = dcc.SETTINGS_UI['I3D_exportGameRelativePath']['defaultValue'], update=setExportRelativePath  )
    I3D_gameLocation              : bpy.props.StringProperty ( name = "Game Location",description="Game Installation Path used for Game Relative Path export option",  default="")
    I3D_gameLocationDisplay       : bpy.props.StringProperty ( name = "Location",description="Game Installation Path used for Game Relative Path export option",  default="", update = setGameLocationPath)
    I3D_exportApplyModifiers      : bpy.props.BoolProperty   ( name = "Apply Modifiers",description="Applies Modifiers if checked",      default = True  )
    I3D_exportAxisOrientations    : bpy.props.EnumProperty   (
                                    items = [   ( "BAKE_TRANSFORMS" , "Bake Transforms" , "Change axis Z = Y" ),
                                    ( "KEEP_TRANSFORMS" , "Keep Transforms" , "Export without any changes" )   ],
                                    name    = "Axis Orientations",
                                    default = "BAKE_TRANSFORMS" )
    I3D_exportUseSoftwareFileName : bpy.props.BoolProperty   ( name = "Use Blender Filename",description="Export Location and Name are the same as the current *.blend File", default = dcc.SETTINGS_UI['I3D_exportUseSoftwareFileName']['defaultValue']  )
    I3D_updateXMLOnExport : bpy.props.BoolProperty   ( name = "Update XML on Export", description="Update the selected XML config Files when Exported",default = dcc.SETTINGS_UI['I3D_updateXMLOnExport']['defaultValue']  )
    I3D_exportFileLocation        : bpy.props.StringProperty ( name = "File Location", description="Target File, if extention does not match, it is replaced by .i3d")
    I3D_predefinedPhysic    : bpy.props.EnumProperty   (
                                    default=0,
                                    items = dcc.UIgetPredefinePhysicItems,
                                    name="Physics",
                                    update=updateFromPredefinePhysic
                                    )
    I3D_predefinedNonPhysic    : bpy.props.EnumProperty   (
                                    default=0,
                                    items = dcc.UIgetPredefineNonPhysicItems,
                                    name="Non Physics",
                                    update=updateFromPredefineNonPhysic
                                    )
    I3D_selectedPredefined :    bpy.props.StringProperty ( name = "Selected Predef.", default = dcc.SETTINGS_ATTRIBUTES['I3D_selectedPredefined']['defaultValue'])
    I3D_predefHasChanged    :   bpy.props.BoolProperty  (name = "Predef change state", default = dcc.SETTINGS_ATTRIBUTES['I3D_predefHasChanged']['defaultValue'])

    I3D_updateXMLFilePath : bpy.props.StringProperty ( name = "XML File Paths",   default = dcc.SETTINGS_UI['I3D_updateXMLFilePath']['defaultValue']  )
    I3D_shaderFolderLocation : bpy.props.StringProperty (name = "Shader Folder", update=onWriteShaderPath)
    I3D_materialSlotName : bpy.props.StringProperty (name = "Slot Name")
    I3D_shadingRate             : bpy.props.EnumProperty(
                items = [ ('1x1' ,  '1x1'   ,  ''),
                          ('1x2',  '1x2', ''),
                          ('2x1',  '2x1', ''),
                          ('2x2',  '2x2', ''),
                          ('2x4',  '2x4', ''),
                          ('4x2',  '4x2', ''),
                          ('4x4',  '4x4', '')],
                name = "Shading Rate"
                )
    I3D_alphaBlending           : bpy.props.BoolProperty ( name = 'Alpha Blending', default = dcc.SETTINGS_ATTRIBUTES['I3D_alphaBlending']['defaultValue'])
    I3D_nodeName              : bpy.props.StringProperty ( name = "Loaded Node",         default = dcc.SETTINGS_UI['I3D_nodeName']['defaultValue'])
    I3D_nodeIndex             : bpy.props.StringProperty ( name = "Node Index",          default = dcc.SETTINGS_UI['I3D_nodeIndex']['defaultValue'] )
    I3D_lockedGroup           : bpy.props.BoolProperty   ( name = "Locked Group",        default = dcc.SETTINGS_ATTRIBUTES['I3D_lockedGroup']['defaultValue'] )
    I3D_static                : bpy.props.BoolProperty   ( name = "Static",              default = dcc.SETTINGS_ATTRIBUTES['I3D_static']['defaultValue'],  description = "passive Rigid Body non movable"  )
    I3D_dynamic               : bpy.props.BoolProperty   ( name = "Dynamic",             default = dcc.SETTINGS_ATTRIBUTES['I3D_dynamic']['defaultValue'], description = "active Rigid Body simulated"     )
    I3D_kinematic             : bpy.props.BoolProperty   ( name = "Kinematic",           default = dcc.SETTINGS_ATTRIBUTES['I3D_kinematic']['defaultValue'], description = "passive Rigid Body movable"      )
    I3D_compound              : bpy.props.BoolProperty   ( name = "Compound",            default = dcc.SETTINGS_ATTRIBUTES['I3D_compound']['defaultValue'], description = "group of Rigid Bodies"           )
    I3D_compoundChild         : bpy.props.BoolProperty   ( name = "Compound Child",      default = dcc.SETTINGS_ATTRIBUTES['I3D_compoundChild']['defaultValue'], description = "part of a group of Rigid Bodies" )
    I3D_collision             : bpy.props.BoolProperty   ( name = "Collision",           default = dcc.SETTINGS_ATTRIBUTES['I3D_collision']['defaultValue']   )
    I3D_solverIterationCount  : bpy.props.IntProperty    ( name = "Solver Iterations",   default = dcc.SETTINGS_ATTRIBUTES['I3D_solverIterationCount']['defaultValue']      )
    I3D_restitution           : bpy.props.FloatProperty  ( name = "Restitution",         default = dcc.SETTINGS_ATTRIBUTES['I3D_restitution']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_staticFriction        : bpy.props.FloatProperty  ( name = "Static Friction",     default = dcc.SETTINGS_ATTRIBUTES['I3D_staticFriction']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_dynamicFriction       : bpy.props.FloatProperty  ( name = "Dynamic Friction",    default = dcc.SETTINGS_ATTRIBUTES['I3D_dynamicFriction']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_linearDamping         : bpy.props.FloatProperty  ( name = "Linear Damping",      default = dcc.SETTINGS_ATTRIBUTES['I3D_linearDamping']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_angularDamping        : bpy.props.FloatProperty  ( name = "Angular Damping",     default = dcc.SETTINGS_ATTRIBUTES['I3D_angularDamping']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_density               : bpy.props.FloatProperty  ( name = "Density",             default = dcc.SETTINGS_ATTRIBUTES['I3D_density']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_ccd                   : bpy.props.BoolProperty   ( name = "Continues Collision Detection" , default = dcc.SETTINGS_ATTRIBUTES['I3D_ccd']['defaultValue']  )
    I3D_trigger               : bpy.props.BoolProperty   ( name = "Trigger",             default = dcc.SETTINGS_ATTRIBUTES['I3D_trigger']['defaultValue']  )
    I3D_splitType             : bpy.props.IntProperty    ( name = "Split Type",          default = dcc.SETTINGS_ATTRIBUTES['I3D_splitType']['defaultValue']  )
    I3D_splitMinU             : bpy.props.FloatProperty  ( name = "Split Min U",         default = dcc.SETTINGS_ATTRIBUTES['I3D_splitMinU']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_splitMinV             : bpy.props.FloatProperty  ( name = "Split Min V",         default = dcc.SETTINGS_ATTRIBUTES['I3D_splitMinV']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_splitMaxU             : bpy.props.FloatProperty  ( name = "Split Max U",         default = dcc.SETTINGS_ATTRIBUTES['I3D_splitMaxU']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_splitMaxV             : bpy.props.FloatProperty  ( name = "Split Max V",         default = dcc.SETTINGS_ATTRIBUTES['I3D_splitMaxV']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_splitUvWorldScale     : bpy.props.FloatProperty  ( name = "Split UV's worldScale",         default = dcc.SETTINGS_ATTRIBUTES['I3D_splitUvWorldScale']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_joint                 : bpy.props.BoolProperty   ( name = "Joint",               default = dcc.SETTINGS_ATTRIBUTES['I3D_joint']['defaultValue']   )
    I3D_projection            : bpy.props.BoolProperty   ( name = "Projection",          default = dcc.SETTINGS_ATTRIBUTES['I3D_projection']['defaultValue']  )
    I3D_projDistance          : bpy.props.FloatProperty  ( name = "Projection Distance", default = dcc.SETTINGS_ATTRIBUTES['I3D_projDistance']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_projAngle             : bpy.props.FloatProperty  ( name = "Projection Angle",    default = dcc.SETTINGS_ATTRIBUTES['I3D_projAngle']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_xAxisDrive            : bpy.props.BoolProperty   ( name = "X-Axis Drive",        default = dcc.SETTINGS_ATTRIBUTES['I3D_xAxisDrive']['defaultValue']  )
    I3D_yAxisDrive            : bpy.props.BoolProperty   ( name = "Y-Axis Drive",        default = dcc.SETTINGS_ATTRIBUTES['I3D_yAxisDrive']['defaultValue']  )
    I3D_zAxisDrive            : bpy.props.BoolProperty   ( name = "Z-Axis Drive",        default = dcc.SETTINGS_ATTRIBUTES['I3D_zAxisDrive']['defaultValue']  )
    I3D_drivePos              : bpy.props.BoolProperty   ( name = "Drive Position",      default = dcc.SETTINGS_ATTRIBUTES['I3D_drivePos']['defaultValue']  )
    I3D_driveForceLimit       : bpy.props.FloatProperty  ( name = "Drive Force Limit",   default = dcc.SETTINGS_ATTRIBUTES['I3D_driveForceLimit']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_driveSpring           : bpy.props.FloatProperty  ( name = "Drive Spring",        default = dcc.SETTINGS_ATTRIBUTES['I3D_driveSpring']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_driveDamping          : bpy.props.FloatProperty  ( name = "Drive Damping",       default = dcc.SETTINGS_ATTRIBUTES['I3D_driveDamping']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_breakableJoint        : bpy.props.BoolProperty   ( name = "Breakable",           default = dcc.SETTINGS_ATTRIBUTES['I3D_breakableJoint']['defaultValue']  )
    I3D_jointBreakForce       : bpy.props.FloatProperty  ( name = "Break Force",         default = dcc.SETTINGS_ATTRIBUTES['I3D_jointBreakForce']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_jointBreakTorque      : bpy.props.FloatProperty  ( name = "Break Torque",        default = dcc.SETTINGS_ATTRIBUTES['I3D_jointBreakTorque']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_oc                    : bpy.props.BoolProperty   ( name = "Occluder",            default = dcc.SETTINGS_ATTRIBUTES['I3D_oc']['defaultValue'] )
    I3D_castsShadows          : bpy.props.BoolProperty   ( name = "Casts Shadows",       default = dcc.SETTINGS_ATTRIBUTES['I3D_castsShadows']['defaultValue']  )    
    I3D_receiveShadows        : bpy.props.BoolProperty   ( name = "Receive Shadows",     default = dcc.SETTINGS_ATTRIBUTES['I3D_receiveShadows']['defaultValue']  )
    I3D_renderedInViewports   : bpy.props.BoolProperty   ( name = "Rendered in Viewports", default = dcc.SETTINGS_ATTRIBUTES['I3D_renderedInViewports']['defaultValue']  )
    I3D_renderedInEnvmap      : bpy.props.BoolProperty   ( name = "Rendered in envmap",    default = dcc.SETTINGS_ATTRIBUTES['I3D_renderedInEnvmap']['defaultValue']  )
    I3D_grassMetaDataProvider : bpy.props.BoolProperty   ( name = "Grass Metadata Provider",    default = dcc.SETTINGS_ATTRIBUTES['I3D_grassMetaDataProvider']['defaultValue']  )
    I3D_grassMesh             : bpy.props.BoolProperty   ( name = "Grass Mesh",          default = dcc.SETTINGS_ATTRIBUTES['I3D_grassMesh']['defaultValue']  )
    I3D_highdDetailMesh       : bpy.props.BoolProperty   ( name = "High Detail Mesh",    default = dcc.SETTINGS_ATTRIBUTES['I3D_highdDetailMesh']['defaultValue']  )
    I3D_nonRenderable         : bpy.props.BoolProperty   ( name = "Non Renderable",      default = dcc.SETTINGS_ATTRIBUTES['I3D_nonRenderable']['defaultValue']  )
    I3D_clipDistance          : bpy.props.FloatProperty  ( name = "Clip Distance",       default = dcc.SETTINGS_ATTRIBUTES['I3D_clipDistance']['defaultValue'], min=0, precision = 1)
    I3D_objectMask            : bpy.props.IntProperty    ( name = "Object Mask",         default = dcc.SETTINGS_ATTRIBUTES['I3D_objectMask']['defaultValue'], min=0)
    I3D_navMeshMask           : bpy.props.IntProperty    ( name = "Nav Mesh Mask",       default = dcc.SETTINGS_ATTRIBUTES['I3D_navMeshMask']['defaultValue'], min=0)
    I3D_doubleSided           : bpy.props.BoolProperty   ( name = "Double Sided",        default = dcc.SETTINGS_ATTRIBUTES['I3D_doubleSided']['defaultValue'] )
    I3D_decalLayer            : bpy.props.IntProperty    ( name = "Decal Layer",         default = dcc.SETTINGS_ATTRIBUTES['I3D_decalLayer']['defaultValue'], min=0, max=9)
    I3D_mergeGroup            : bpy.props.IntProperty    ( name = "Merge Group",         default = dcc.SETTINGS_ATTRIBUTES['I3D_mergeGroup']['defaultValue'], min=0, max=9)
    I3D_mergeGroupRoot        : bpy.props.BoolProperty   ( name = "Merge Group Root",    default = dcc.SETTINGS_ATTRIBUTES['I3D_mergeGroupRoot']['defaultValue'])
    I3D_boundingVolume        : bpy.props.StringProperty ( name = "Bounding Volume",     default = dcc.SETTINGS_ATTRIBUTES['I3D_boundingVolume']['defaultValue'])
    I3D_boundingVolumeMergeGroup  : bpy.props.EnumProperty ( items = [
                                                                ("MERGEGROUP_1", "Merge Group 1", "Set bounding Volume for merge group 1"),
                                                                ("MERGEGROUP_2", "Merge Group 2", "Set bounding Volume for merge group 2"),
                                                                ("MERGEGROUP_3", "Merge Group 3", "Set bounding Volume for merge group 3"),
                                                                ("MERGEGROUP_4", "Merge Group 4", "Set bounding Volume for merge group 4"),
                                                                ("MERGEGROUP_5", "Merge Group 5", "Set bounding Volume for merge group 5"),
                                                                ("MERGEGROUP_6", "Merge Group 6", "Set bounding Volume for merge group 6"),
                                                                ("MERGEGROUP_7", "Merge Group 7", "Set bounding Volume for merge group 7"),
                                                                ("MERGEGROUP_8", "Merge Group 8", "Set bounding Volume for merge group 8"),
                                                                ("MERGEGROUP_9", "Merge Group 9", "Set bounding Volume for merge group 9")],
                                                             name = "",
                                                             update = boundingVolumeMergeGroupUpdate)
    
    I3D_selectedMaterialEnum : bpy.props.EnumProperty(items = I3D_PT_PanelExport.getMaterials,
                                                     name = "Selected Material",
                                                     update = selectedMaterialEnumUpdate,
                                                     get = None, set = None)
    I3D_shaderEnum : bpy.props.EnumProperty(items = I3D_PT_PanelExport.getShadersFromDirectory,
                                            name = "Shader File",
                                            update=shaderEnumUpdate, get=None, set=None)
    I3D_shaderVariationEnum : bpy.props.EnumProperty(items = I3D_PT_PanelExport.getShaderVariations,
                                            name = "Shader Variation",
                                            update=shaderVariationEnumUpdate, get=None, set=None)
    I3D_mergeChildren   : bpy.props.BoolProperty(name="Merge Children", default = dcc.SETTINGS_ATTRIBUTES['I3D_mergeChildren']['defaultValue'])
    I3D_mergeChildrenFreezeRotation : bpy.props.BoolProperty(name="Rotation", default = dcc.SETTINGS_ATTRIBUTES['I3D_mergeChildrenFreezeRotation']['defaultValue'])
    I3D_mergeChildrenFreezeTranslation  : bpy.props.BoolProperty(name="Translation", default = dcc.SETTINGS_ATTRIBUTES['I3D_mergeChildrenFreezeTranslation']['defaultValue'])
    I3D_mergeChildrenFreezeScale    : bpy.props.BoolProperty(name="Scale", default = dcc.SETTINGS_ATTRIBUTES['I3D_mergeChildrenFreezeScale']['defaultValue'])

    I3D_terrainDecal          : bpy.props.BoolProperty   ( name = "Terrain Decal",       default = dcc.SETTINGS_ATTRIBUTES['I3D_terrainDecal']['defaultValue']  )
    I3D_cpuMesh               : bpy.props.BoolProperty   ( name = "CPU Mesh",            default = dcc.SETTINGS_ATTRIBUTES['I3D_cpuMesh']['defaultValue']  )
    I3D_lod                   : bpy.props.BoolProperty   ( name = "LOD",                 default = dcc.SETTINGS_ATTRIBUTES['I3D_lod']['defaultValue']  )
    I3D_lod0                  : bpy.props.FloatProperty  ( name = "Child 0 Distance",    default = 0, precision = 1 )
    I3D_lod1                  : bpy.props.FloatProperty  ( name = "Child 1 Distance",    default = dcc.SETTINGS_ATTRIBUTES['I3D_lod1']['defaultValue'], min = 0, precision = 1 )
    I3D_lod2                  : bpy.props.FloatProperty  ( name = "Child 2 Distance",    default = dcc.SETTINGS_ATTRIBUTES['I3D_lod2']['defaultValue'], min = 0, precision = 1 )
    I3D_lod3                  : bpy.props.FloatProperty  ( name = "Child 3 Distance",    default = dcc.SETTINGS_ATTRIBUTES['I3D_lod3']['defaultValue'], min = 0, precision = 1 )
    I3D_lodBlending           : bpy.props.BoolProperty  ( name = "LOD Blending",    default = dcc.SETTINGS_ATTRIBUTES['I3D_lodBlending']['defaultValue'] )
    I3D_vertexCompressionRange: bpy.props.EnumProperty   (
                                    items = [
                                        ("Auto", "Auto", ""),
                                        ("0.5", "0.5", ""),
                                        ("1", "1", ""),
                                        ("2", "2", ""),
                                        ("4", "4", ""),
                                        ("8", "8", ""),
                                        ("16", "16", ""),
                                        ("32", "32", ""),
                                        ("64", "64", ""),
                                        ("128", "128", ""),
                                        ("256", "256", ""),
                                    ],
                                    name="Vertex Compression Range",)

    I3D_minuteOfDayStart      : bpy.props.IntProperty       ( name = "Minute Of Day Start",          default = dcc.SETTINGS_ATTRIBUTES['I3D_minuteOfDayStart']['defaultValue'] )
    I3D_minuteOfDayEnd        : bpy.props.IntProperty       ( name = "Minute Of Day End",            default = dcc.SETTINGS_ATTRIBUTES['I3D_minuteOfDayEnd']['defaultValue'] )
    I3D_dayOfYearStart        : bpy.props.IntProperty       ( name = "Day Of Year Start",            default = dcc.SETTINGS_ATTRIBUTES['I3D_dayOfYearStart']['defaultValue'] )
    I3D_dayOfYearEnd          : bpy.props.IntProperty       ( name = "Day Of Year End",              default = dcc.SETTINGS_ATTRIBUTES['I3D_dayOfYearEnd']['defaultValue'] )
    I3D_weatherMask           : bpy.props.StringProperty    ( name = "Weather Mask (Dec)",           default = dcc.SETTINGS_ATTRIBUTES['I3D_weatherMask']['defaultValue'] )
    I3D_viewerSpacialityMask  : bpy.props.StringProperty    ( name = "Viewer Spaciality Mask (Dec)", default = dcc.SETTINGS_ATTRIBUTES['I3D_viewerSpacialityMask']['defaultValue'] )
    I3D_weatherPreventMask      :bpy.props.StringProperty   ( name = "Weather Prevent Mask (Dec)",  default = dcc.SETTINGS_ATTRIBUTES['I3D_weatherPreventMask']['defaultValue'])
    I3D_viewerSpacialityPreventMask      :bpy.props.StringProperty   ( name = "Viewer Spaciality Prevent Mask (Dec)",  default = dcc.SETTINGS_ATTRIBUTES['I3D_viewerSpacialityPreventMask']['defaultValue'])
    I3D_renderInvisible         :bpy.props.BoolProperty     ( name = "Render Invisible",            default = dcc.SETTINGS_ATTRIBUTES['I3D_renderInvisible']['defaultValue'])
    I3D_visibleShaderParam      :bpy.props.FloatProperty    ( name = "Visible Shader Param",        default = dcc.SETTINGS_ATTRIBUTES['I3D_visibleShaderParam']['defaultValue'] , precision = dcc.FLOAT_PRECISION )
    I3D_forceVisibilityCondition :bpy.props.BoolProperty     ( name = "Force Visibility Condition", default = dcc.SETTINGS_ATTRIBUTES['I3D_forceVisibilityCondition']['defaultValue'])

    I3D_objectDataFilePath                : bpy.props.StringProperty ( name = "File Path",           default = dcc.SETTINGS_ATTRIBUTES['I3D_objectDataFilePath']['defaultValue'])
    I3D_objectDataHierarchicalSetup       : bpy.props.BoolProperty   ( name = "Hierarchical Setup",  default = dcc.SETTINGS_ATTRIBUTES['I3D_objectDataHierarchicalSetup']['defaultValue']  )
    I3D_objectDataHideFirstAndLastObject  : bpy.props.BoolProperty   ( name = "HideFirst And Last",  default = dcc.SETTINGS_ATTRIBUTES['I3D_objectDataHideFirstAndLastObject']['defaultValue']  )
    I3D_objectDataExportPosition          : bpy.props.BoolProperty   ( name = "Export Position",     default = dcc.SETTINGS_ATTRIBUTES['I3D_objectDataExportPosition']['defaultValue']  )
    I3D_objectDataExportOrientation       : bpy.props.BoolProperty   ( name = "Export Orientation",  default = dcc.SETTINGS_ATTRIBUTES['I3D_objectDataExportOrientation']['defaultValue']  )
    I3D_objectDataExportScale             : bpy.props.BoolProperty   ( name = "Export Scale",        default = dcc.SETTINGS_ATTRIBUTES['I3D_objectDataExportScale']['defaultValue']  )

    I3D_softShadowsLightSize       : bpy.props.FloatProperty  ( name = "Soft Shadow Light Size",        default = dcc.SETTINGS_ATTRIBUTES["I3D_softShadowsLightSize"]["defaultValue"] )
    I3D_softShadowsLightDistance   : bpy.props.FloatProperty  ( name = "Soft Shadow Light Distance",    default = dcc.SETTINGS_ATTRIBUTES["I3D_softShadowsLightDistance"]["defaultValue"] )
    I3D_softShadowsDepthBiasFactor : bpy.props.FloatProperty  ( name = "Soft Shadow Depth Bias Factor", default = dcc.SETTINGS_ATTRIBUTES["I3D_softShadowsDepthBiasFactor"]["defaultValue"] )
    I3D_softShadowsMaxPenumbraSize : bpy.props.FloatProperty  ( name = "Soft Shadow Max Penumbra Size", default = dcc.SETTINGS_ATTRIBUTES["I3D_softShadowsMaxPenumbraSize"]["defaultValue"] )
    I3D_iesProfileFile             : bpy.props.StringProperty ( name = "IES Profile File",              default = dcc.SETTINGS_ATTRIBUTES['I3D_iesProfileFile']['defaultValue'] )

    @classmethod
    def register( cls ):
        bpy.types.Scene.I3D_UIexportSettings = bpy.props.PointerProperty(
            name = "I3D UI Export Settings",
            type =  cls,
            description = "I3D UI Export Settings"
        )
    @classmethod
    def unregister( cls ):
        if bpy.context.scene.get( 'I3D_UIexportSettings' ):  del bpy.context.scene[ 'I3D_UIexportSettings' ]
        try:    del bpy.types.Scene.I3D_UIexportSettings
        except: pass

#-------------------------------------------------------------------------------
#   Handlers
#-------------------------------------------------------------------------------
@persistent
def load_handler(dummy):
    """ not executed if addon is enabled in the preferences, only on load file (eg. startup or load file)"""

    try:
        if 'I3D_gameLocationDisplay' in bpy.context.scene.I3D_UIexportSettings :
            if not os.path.isdir(bpy.context.scene.I3D_UIexportSettings['I3D_gameLocationDisplay']):
                if bpy.context.scene.I3D_UIexportSettings['I3D_gameLocationDisplay'] == "":
                    pass
                else:
                    print("\"" + bpy.context.scene.I3D_UIexportSettings['I3D_gameLocationDisplay'] + "\" is no valid game path")
                    bpy.context.scene.I3D_UIexportSettings['I3D_gameLocationDisplay'] = dirf.findFS22Path()
                    print("new path: " +bpy.context.scene.I3D_UIexportSettings['I3D_gameLocationDisplay'])
    except Exception as e:
        print(e)

    # Handle legacy locked groups
    legacyLockedGroupAttributeName = 'I3D_lockedGroup'
    if legacyLockedGroupAttributeName in bpy.context.scene.I3D_UIexportSettings:
        if bpy.context.scene.I3D_UIexportSettings[legacyLockedGroupAttributeName] == True:
            for m_node in bpy.context.scene.objects:
                if (None is m_node.parent):
                    m_node['I3D_lockedGroup'] = True
        bpy.context.scene.I3D_UIexportSettings[legacyLockedGroupAttributeName] = 0
    # End handle legacy locked groups

 
@persistent
def modal_handler(dummy):
    global g_modalsRunning

    try:
        bpy.ops.i3d.active_object('INVOKE_DEFAULT')
        bpy.ops.i3d.predef_check('INVOKE_DEFAULT')
        g_modalsRunning = True
        if gS4MaterialPanel != None:
            gS4MaterialPanel.handlePostLoad()
        if gS4ShapePanel != None:
            gS4ShapePanel.handlePostLoad()
    except Exception as e:
        print(e)


editMeshContextMenuClasses = [I3D_OT_FaceNormalToOrigin, I3D_OT_SelectionToOrigin, I3D_OT_CreateEmpty]
def drawEditMeshContextMenu(self, context):
    isFirstItem = True
    for editMeshContextMenuClass in editMeshContextMenuClasses:
        if editMeshContextMenuClass.getShowInContextMenu(context):
            if isFirstItem:
                self.layout.separator()
                isFirstItem = False

            self.layout.operator(editMeshContextMenuClass.bl_idname, icon=editMeshContextMenuClass.CONTEXT_MENU_ICON)

objectContextMenuClasses = [I3D_OT_CreateEmpty, I3D_OT_AlignYAxis, I3D_OT_FreezeTranslation, I3D_OT_FreezeRotation]
def drawObjectContextMenu(self, context):
    isFirstItem = True
    for objectContextMenuClass in objectContextMenuClasses:
        if objectContextMenuClass.getShowInContextMenu(context):
            if isFirstItem:
                self.layout.separator()
                isFirstItem = False

            self.layout.operator(objectContextMenuClass.bl_idname, icon=objectContextMenuClass.CONTEXT_MENU_ICON)



            import bpy


class I3D_OT_show_chop_dialog(bpy.types.Operator):
    bl_idname = "i3d.show_chop_dialog"
    bl_label = "Show Chop Dialog"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        bpy.ops.wm.i3d_chop_dialog('INVOKE_DEFAULT')
        return {'FINISHED'}

class I3D_OT_chop_dialog(bpy.types.Operator):
    bl_idname = "wm.i3d_chop_dialog"
    bl_label = "Chop Mesh by Size"
    
    max_sizeX: bpy.props.FloatProperty(
        name="Max Size X",
        description="Maximum size for each chopped part",
        default=10.0,
        min=0.0,
    )
    max_sizeY: bpy.props.FloatProperty(
        name="Max Size Y",
        description="Maximum size for each chopped part",
        default=10.0,
        min=0.0,
    )
    max_sizeZ: bpy.props.FloatProperty(
        name="Max Size Z",
        description="Maximum size for each chopped part",
        default=10.0,
        min=0.0,
    )

    def execute(self, context):
        self.report({'INFO'}, f"OK: Chopping mesh with max size {self.max_sizeX} {self.max_sizeY} {self.max_sizeZ}")
        print(f"OK: Chopping mesh with max size {self.max_sizeX} {self.max_sizeY} {self.max_sizeZ}")
        object_names = selectionUtil.getSelectedNodes()
        for name in object_names:
            obj = bpy.data.objects.get(name)
            if obj and obj.type == 'MESH' :
                chopped_objects = meshchoppingUtil.chop_mesh_by_size(obj, self.max_sizeX,self.max_sizeY,self.max_sizeZ)
                #if len(chopped_objects) > 0 :
                #    bpy.data.objects.remove(obj, do_unlink=True)

              
        return {'FINISHED'}
    
    def cancel(self, context):
        self.report({'INFO'}, "Cancel: Operation was canceled")
        print("Cancel: Operation was canceled")
        return {'CANCELLED'}
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "max_sizeX")
        layout.prop(self, "max_sizeY")
        layout.prop(self, "max_sizeZ")
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


def meshchopping_menu_func(self, context):
    self.layout.operator(I3D_OT_show_chop_dialog.bl_idname)



#-------------------------------------------------------------------------------
#   Register
#-------------------------------------------------------------------------------
classes = (
        I3D_UIMaterialTemplateProperties,
        I3D_PT_PanelExport,
        I3D_OT_PanelExport_ButtonAttr,
        I3D_OT_PanelExport_ButtonExport,
        I3D_OT_PanelRemoveXMLPath_ButtonRemove,
        I3D_OT_PanelAddShader_ButtonAdd,
        I3D_OT_PanelExport_ButtonClose,
        I3D_OT_PanelUpdateXMLi3dmapping,
        I3D_OT_PanelXMLidentification_ButtonAdd,
        I3D_OT_PanelOpenXMLFilebrowser,
        I3D_OT_PanelOpenFolderFilebrowser,
        I3D_OT_PanelRefreshGamePath,
        I3D_OT_PanelAddShader_ButtonLoad,
        I3D_OT_PanelSetGameShader,
        I3D_OT_PanelOpenI3DFilebrowser,
        I3D_OT_PanelOpenDDSFilebrowser,
        I3D_OT_PanelOpenIESFilebrowser,
        I3D_OT_PanelTools_Button,
        I3D_OT_PanelMaterial_OpenMaterialTemplatesWindowButton,
        I3D_OT_PanelMaterial_UseMaterialNameAsSlotNameButton,
        I3D_OT_PanelMaterial_ApplyMaterialTemplateToSelection,
        I3D_OT_modal_active_object,
        I3D_OT_modal_predef_check,
        I3D_OT_BitmaskEditor,
        #I3D_OT_MaterialTemplateCategoryMenuItemExpand,
        I3D_OT_MaterialTemplateCategoryMenu,
        I3D_OT_MaterialTemplateCategoryMenuEntryExpand,
        #I3D_MaterialTemplateCategoryMenuItem,
        #I3D_UL_MaterialTemplateCategoryMenu
)

def register():
    bpy.utils.register_class( I3D_UIexportSettings )
    bpy.utils.register_class( I3D_OT_MenuExport )
    bpy.utils.register_class( I3D_OT_SelectionToOrigin )
    bpy.utils.register_class( I3D_OT_FaceNormalToOrigin )
    bpy.utils.register_class( I3D_OT_FreezeTranslation )
    bpy.utils.register_class( I3D_OT_FreezeRotation )
    bpy.utils.register_class( I3D_OT_CreateEmpty )
    bpy.utils.register_class( I3D_OT_AlignYAxis )

    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Error: unable to register class {cls}: {e}")

    # --------------------------New Material Panel Operators-------------------------------------------
    registerMaterialPanelItems()
    # --------------------------New Shape Panel Operators-------------------------------------------
    registerShapePanelItems()
     # --------------------------Tools-------------------------------------------
    registerTools()
    # --------------------------Handler-------------------------------------------
    bpy.app.handlers.load_post.append(load_handler)
    bpy.app.handlers.load_post.append(modal_handler)
    # --------------------------Context Menu-------------------------------------------
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(drawEditMeshContextMenu)
    bpy.types.VIEW3D_MT_object_context_menu.append(drawObjectContextMenu)

    bpy.utils.register_class(I3D_OT_show_chop_dialog)
    bpy.utils.register_class(I3D_OT_chop_dialog)
    bpy.types.OUTLINER_MT_object.append(meshchopping_menu_func)


def unregister():
    bpy.utils.unregister_class(I3D_OT_show_chop_dialog)
    bpy.utils.unregister_class(I3D_OT_chop_dialog)
    bpy.types.OUTLINER_MT_object.remove(meshchopping_menu_func)
 

    for dynamicClass in g_dynamicGUIClsDict.values():
        bpy.utils.unregister_class(dynamicClass)
    # --------------------------Tools-------------------------------------------
    unregisterTools()
    # --------------------------------------------------------------------------
    # --------------------------New Material Panel Operators-------------------------------------------
    unregisterMaterialPanelItems()
    # --------------------------New Shape Panel Operators-------------------------------------------
    unregisterShapePanelItems()
    # --------------------------------------------------------------------------
  
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            print(f"Error: unable to unregister class {cls}")
    # --------------------------------------------------------------------------
    bpy.utils.unregister_class( I3D_OT_SelectionToOrigin )
    bpy.utils.unregister_class( I3D_OT_FaceNormalToOrigin )
    bpy.utils.unregister_class( I3D_OT_FreezeTranslation )
    bpy.utils.unregister_class( I3D_OT_FreezeRotation )
    bpy.utils.unregister_class( I3D_OT_CreateEmpty )
    bpy.utils.unregister_class( I3D_OT_AlignYAxis )
    bpy.utils.unregister_class( I3D_OT_MenuExport )
    bpy.utils.unregister_class( I3D_UIexportSettings )


    bpy.app.handlers.load_post.remove(modal_handler)
    bpy.app.handlers.load_post.remove(load_handler)

    # --------------------------Context Menu-------------------------------------------
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(drawEditMeshContextMenu)
    bpy.types.VIEW3D_MT_object_context_menu.remove(drawObjectContextMenu)

    global g_modalsRunning
    g_modalsRunning = False
#-------------------------------------------------------------------------------