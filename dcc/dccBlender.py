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

import bpy, bmesh
from ctypes import c_int, c_float, c_void_p, c_short, \
    c_char, c_char_p, c_uint, POINTER, Structure
from time import monotonic
import os
import shutil
import re
import math, mathutils
from ..util import logUtil, i3d_densityUtil, selectionUtil, i3d_shaderUtil
from ..util import i3d_directoryFinderUtil as dirf
import copy
import numpy as np
import hashlib
import xml.etree.ElementTree as ET


def getFilePath():
    return bpy.path.ensure_ext( os.path.splitext(bpy.data.filepath)[0], ".i3d" )    #remove .blend from path

def getFileBasename():
    return bpy.path.basename( bpy.data.filepath )

def getAbsPath(path):
    return bpy.path.abspath(path)

def isFileSaved():
    if bpy.data.filepath:
        return True
    else:
        return False

def appVersion():
    return bpy.app.version

def UISetLoadedNode(nodeStr):
    if(nodeStr in bpy.data.objects):
        node = bpy.data.objects[nodeStr]
        UISetAttrString("I3D_nodeName",node.name)
        UISetAttrString("I3D_nodeIndex",getNodeIndex(node.name))

def UIGetLoadedNode():
    objPath = UIGetAttrString("I3D_nodeName")
    if (objPath in bpy.data.objects):
        return objPath
    else:
        return None

def I3DAddAttrBool(nodeStr,attr):
    I3DSetAttrBool(nodeStr,attr,bool(False))

def I3DSetAttrBool(nodeStr,attr,val):
    node = bpy.data.objects[nodeStr]
    node[attr] = val

def I3DAddAttrInt(nodeStr,attr):
    I3DSetAttrInt(nodeStr,attr,int(0))

def I3DSetAttrInt(nodeStr,attr,val):
    node = bpy.data.objects[nodeStr]
    node[attr] = val

def I3DAddAttrFloat(nodeStr,attr):
    I3DSetAttrFloat(nodeStr,attr,float(0.0))

def I3DSetAttrFloat(nodeStr,attr,val):
    m_node = bpy.data.objects[nodeStr]
    m_node[attr] = round(val, 6)     #gui elements are not very exact

def I3DAddAttrString(nodeStr,attr):
    I3DSetAttrString(nodeStr,attr,str(""))

def I3DSetAttrString(nodeStr,attr,val):
    node = bpy.data.objects[nodeStr]
    node[attr] = val

def I3DAddAttrEnum(nodeStr,attr):
    I3DSetAttrEnum(nodeStr,attr,"None")

def I3DSetAttrEnum(nodeStr, attr, val):
    node = bpy.data.objects[nodeStr]
    node[attr] = val

def I3DGetAttr(nodeStr, attr):
    node = bpy.data.objects[nodeStr]
    if(attr == "I3D_boundingVolume" and node[attr] == ""):    #backwards compatibility
        node[attr] = 'None'
    return node[attr]

def I3DAttributeExists(nodeStr, attr):
    if nodeStr in bpy.data.objects:
        m_node = bpy.data.objects[nodeStr]
        if (attr in m_node):
            return True
    return False

def I3DRemoveAttribute(nodeStr, attr):
    node = bpy.data.objects[nodeStr]
    if(I3DAttributeExists(nodeStr, attr)):
        del node[attr]

def getXMLConfigID(nodeStr):
    try:
        return bpy.data.objects[nodeStr]["I3D_XMLconfigID"]
    except:
        return nodeStr

def getXMLConfigBool(nodeStr):
    try:
        return bpy.data.objects[nodeStr]["I3D_XMLconfigBool"] == 1
    except:
        return False

def UIAttrExists(attr):
    try:
        m_str = "bpy.context.scene.I3D_UIexportSettings.{0}".format(attr)
        eval(m_str)
        return True
    except Exception as exception:
        UIShowError(exception)
        return False

def UIGetAttrBool(key):
    m_str = "bpy.context.scene.I3D_UIexportSettings.{0}".format(key)
    return eval(m_str)

def UISetAttrBool(key,val):
    m_str = "bpy.context.scene.I3D_UIexportSettings.{0}=bool({1})".format(key,val)
    exec(m_str)

def UIGetAttrInt(key):
    m_str = "bpy.context.scene.I3D_UIexportSettings.{0}".format(key)
    return eval(m_str)

def UISetAttrInt(key, val):
    m_str = "bpy.context.scene.I3D_UIexportSettings.{0}=int({1})".format(key,val)
    exec(m_str)

def UIGetAttrFloat(key):
    m_str = "bpy.context.scene.I3D_UIexportSettings.{0}".format(key)
    return eval(m_str)

def UISetAttrFloat(key, val):
    m_str = "bpy.context.scene.I3D_UIexportSettings.{0}=float({1})".format(key,val)
    exec(m_str)

def UIGetAttrString(key):
    return getattr(bpy.context.scene.I3D_UIexportSettings, key)

def UISetAttrString(key, val):
    setattr(bpy.context.scene.I3D_UIexportSettings, key, str(val))

def UIGetAttrEnum(key):
    string = "bpy.context.scene.I3D_UIexportSettings.{0}".format(key)
    return eval(string)

def UISetAttrEnum(key, val):
    UISetAttrString(key,val)

def UIShowError(errorMsg):
    if (UIGetAttrBool('I3D_exportVerbose')):
        # print("Error: {0}".format(errorMsg))
        logUtil.ActionLog.addMessage(errorMsg, messageType = 'ERROR')

def UIShowWarning(warningMsg):
    if (UIGetAttrBool('I3D_exportVerbose')):
        # print("Warning: {0}".format(warningMsg))
        logUtil.ActionLog.addMessage(warningMsg,messageType = 'WARNING')

def UIAddMessage(msg):
    if (UIGetAttrBool('I3D_exportVerbose')):
        # print(msg)
        logUtil.ActionLog.addMessage(msg)



def getSelectedNodes():
    """ Returns a list of all bpy.context.selected_objects names. """

    return selectionUtil.getSelectedNodes()


def getSelectedNodesToExport():
    """ Returns a list with all bpy.context.selected_objects and its parents. """

    iterItems = []
    nodes = getSelectedNodes()
    for nodeStr in nodes:
        iterItems.append(nodeStr)
        addParentNodeToList(nodeStr,iterItems)
    iterItems.sort(key=natural_keys)
    return iterItems

def addParentNodeToList(nodeStr,iterItems):
    """ Appends all parents of bpy.data.object[nodeStr] up to the root to iterItems. """

    parentStr = getParentObjectWithoutWorld(nodeStr)
    if (parentStr):
        if (parentStr not in iterItems):
            iterItems.append(parentStr)
        addParentNodeToList(parentStr, iterItems)
    else:
        return iterItems

def isParentedToWorld(nodeStr):
    """ Returns True if there exists no parent. """

    node = bpy.data.objects[nodeStr]
    parent = node.parent
    if (None==parent):
        return True
    else:
        return False

def getAllNodesToExport():
    """ Returns a list with all bpy.data.objects names """

    result = []
    nodes = getWorldObjects()
    addChildObjects(nodes,result)
    return result

def getParentObjectWithoutWorld(nodeStr):
    """ Returns the parent object name of nodeStr if existing """

    node = bpy.data.objects[nodeStr]
    # if parented to the world return None
    if node.parent:
        return node.parent.name
    else:
        return None

def getChildObjects(parentStr):
    """Returns a sorted list of all children names of the given parent object."""
    parent = bpy.data.objects.get(parentStr)
    if not parent:
        return []

    # Using a list comprehension for better performance
    iterItems = [child.name for child in parent.children]
    iterItems.sort(key=natural_keys)
    return iterItems

def getNodeInstances(nodeStr):
    """ Returns [], only placeholder implementation """

    nodes = []
    return nodes

def getFormattedNodeName(nodeName):
    """ Formats a given node name for export (removal of sorting prefix) """
    return nodeName.split(":")[-1]

def getNodeName(nodeStr):
    """ Get bpy.data.object[].name """

    return getFormattedNodeName(bpy.data.objects[nodeStr].name)

def getNodeData(nodeStr, nodeData = {}):
    """ returns a dictionary with the basic data of the bpy.data.objects[nodeStr] object"""

    nodeObj = bpy.data.objects[nodeStr]
    nodeData["fullPathName"] = nodeObj.name
    nodeData["name"] = getNodeName(nodeStr)
    nodeData["type"] = getNodeType(nodeStr)
    return nodeData

def getBoneData(boneStr, armStr, nodeData = {}):
    """ Gets bpy.data of the requested bone and writes it to nodeData """

    boneObj = bpy.data.objects[armStr].data.bones[boneStr]
    nodeData["fullPathName"] = armStr + "_" + boneObj.name
    nodeData["name"] = boneObj.name
    return nodeData

def transformPath(objStr, inverted = False):
    """ Recursively calculates the translation of the objStr object to the root object"""

    obj = bpy.data.objects[objStr]
    objMat = obj.matrix_local
    if ( "BAKE_TRANSFORMS"  == UIGetAttrString('I3D_exportAxisOrientations')): #meshTransformation
        objMat = bakeTransformMatrix(objMat)
    if obj.parent:
        if inverted:
            return (objMat.inverted() @ transformPath(obj.parent.name, inverted= inverted)).inverted()
        else:
            return objMat @ transformPath(obj.parent.name)
    else:
        if inverted:
            return objMat.inverted()
        else:
            return objMat

# Define the custom exception class
class MergeStructureMismatchException(Exception):
    def __init__(self, message):
        super().__init__(message)    
    

def getMergeGroupShapeData(shapeNameStr, shapeData, sceneNodeData):
    """
    Merges the shape data of multiple shapes according to the settings provided

    differs I3D_mergeChildren and others which should be merge groups. These two modes are very similar, but request slightly different datasets
    merge Children merges all children objects, merge groups combines all objects from ["mergeGroupMember"]

    :param shapeNameStr: the name of the shape
    :param shapeData: the dictionary for the return value
    :param sceneNodeData: the SceneNodeData with the detailed export settings
    :returns: dictionary shapeData
    """

    mergeChildrevDivider = 32767    #fixed value
    if ("I3D_mergeChildren" in sceneNodeData):  #mergeChildren
        rootName = "ORIGIN"
        mergeData = {}
        #shapeNameStr is MergedChildren
        for i in range(len(sceneNodeData["children"])):
            child = sceneNodeData["children"][i]
            g = i/mergeChildrevDivider
            freezeRot = False
            freezeTrans = False
            freezeScale = False
            if 'I3D_mergeChildrenFreezeRotation' in sceneNodeData:
                freezeRot = sceneNodeData['I3D_mergeChildrenFreezeRotation'] == 1
                rootName = shapeNameStr
            if 'I3D_mergeChildrenFreezeTranslation' in sceneNodeData:
                freezeTrans = sceneNodeData['I3D_mergeChildrenFreezeTranslation'] == 1
                rootName = shapeNameStr
            if 'I3D_mergeChildrenFreezeScale' in sceneNodeData:
                freezeScale = sceneNodeData['I3D_mergeChildrenFreezeScale'] == 1
                rootName = shapeNameStr
            memberResult = getMergeMemberShapeData(child, float(g),rootName,freezeTrans,freezeRot,freezeScale)      # g is a multiple of 1/32767, one g value per mesh, detect empty for a g increase
            if memberResult:
                if ("I3D_cpuMesh" in sceneNodeData):
                    memberResult["meshUsage"] = getMeshUsage(sceneNodeData["I3D_cpuMesh"])
                if i == 0:
                    shapeData = memberResult
                    mergeData[i] = memberResult
                else:
                    mergeData[i] = memberResult

        if (not overrideBV(shapeNameStr, shapeData, sceneNodeData)):
            #BV-values loop
            bVmergeData = {}
            for i in range(len(sceneNodeData["children"])):
                child = sceneNodeData["children"][i]
                bvMemberResult = getMergeMemberShapeData(child, float(0),shapeNameStr, True,True,True)      # g is a multiple of 1/32767 one g value per mesh, detect empty for a g increase
                if bvMemberResult:
                    bVmergeData[i] = bvMemberResult
            vSum = mathutils.Vector((0,0,0))
            bvCenter = mathutils.Vector((0,0,0)) #TODO: check init value
            bvRadius = 0
            vCount = 0
            # print([vert["p"] for vert in [vertItem for vertItemsLists in [i["Vertices"]["data"] for k,i in bVmergeData.items()] for vertItem in vertItemsLists]])
            vertPos = [vert["p"] for vert in [vertItem for vertItemsLists in [i["Vertices"]["data"] for k,i in bVmergeData.items()] for vertItem in vertItemsLists]]
            for v in vertPos:
                pos = v.strip().split(" ")
                vSum += mathutils.Vector((float(pos[0]),float(pos[1]),float(pos[2])))        #x,y,z vector
                vCount += 1
                bvCenter = vSum / vCount
            for v in vertPos:
                pos = v.strip().split(" ")
                vect = bvCenter - mathutils.Vector((float(pos[0]),float(pos[1]),float(pos[2])))
                bvRadius = max(vect.length, bvRadius )

            shapeData["bvCenter"] = "{:g} {:g} {:g}".format(bvCenter.x,bvCenter.y,bvCenter.z)
            shapeData["bvRadius"] = "{:g}".format(bvRadius)

        shapeData['name'] = "MergedChildren{:d}".format(sceneNodeData["id"])       # rename the shape to MergedChildrenX
        shapeData['isOptimized'] = "false"
    else:   #mergeGroup
        rootName = getMeshOwners(shapeNameStr)[0]
        mergeData = {}
        skinBindStr = ""
        for index in range(0,len(sceneNodeData["mergeGroupMember"])):
            memberNameStr = sceneNodeData['mergeGroupMember'][index]
            memberId = sceneNodeData['skinBindNodeIds'][index]
            # print("index: "+str(index) + " memberName: " + str(memberNameStr) + " memberId: " +str(memberId))
            memberResult = getMergeMemberShapeData(memberNameStr, int(index),rootName, True,True,True)
            if(rootName == memberNameStr):              #merge root
                shapeData = memberResult                #initialize shapeData
                mergeData[index] = memberResult
                skinBindStr = skinBindStr + "{:d} ".format(memberId)
            else:
                mergeData[index] = memberResult
                skinBindStr = skinBindStr + "{:d} ".format(memberId)
        overrideBV(shapeNameStr, shapeData, sceneNodeData)
        shapeData['name'] = "mergeGroupShape{:d}".format(sceneNodeData['mergeGroupNum'])
        shapeData['isOptimized'] = "false"
        shapeData['skinBindNodeIds'] = skinBindStr

    if 'I3D_vertexCompressionRange' in sceneNodeData:
        shapeData['vertexCompressionRange'] = sceneNodeData['I3D_vertexCompressionRange']

    #merge results
    #integrate all items of mergeData into the shapeData structure
    finalVertexBuffer = []
    finalExtraVertexBuffer = []
    
    finalIndexBuffer = []
    finalSubsets = []
    finalMaterials = []
    finalTriangles = []
    vertexBufferDict = {}
    extravertexBufferDict = {}
    indexBufferDict = {}
    
    #kb we need to sort out stuff here for merging the extra 
    extraFormats = None
    
    for k, item in mergeData.items():

        if 	"dataFormats" not in shapeData["Vertices"]:
            shapeData["Vertices"]["dataFormats"] = item["Vertices"]["dataFormats"]
        else:
            if shapeData["Vertices"]["dataFormats"] != item["Vertices"]["dataFormats"]:
                raise MergeStructureMismatchException(f"Structures do not match in merge meshes")

			
        if 	"extraDataFormats" not in shapeData["Vertices"]:
            extraFormats = item["Vertices"]["extraDataFormats"]
        else:
            if extraFormats != item["Vertices"]["extraDataFormats"]:
                raise MergeStructureMismatchException(f"Structures do not match in merge meshes")
    		
    
        vertexBuffer = []
        extravertexBuffer = []
        indexBuffer = []
        for vertex in item["Vertices"]['data']:
            vertexBuffer.append(vertex)
      
        if 'extraData' in  item["Vertices"]	:	
            for vertex in item["Vertices"]['extraData']:
	            extravertexBuffer.append(vertex)
 
        for triangle in item["Triangles"]['data']:
            for trianlgeEntry in triangle.values():
                for index in trianlgeEntry.strip().split(" "):
                    indexBuffer.append(int(index))
        vertexBufferDict[k] = vertexBuffer
        extravertexBufferDict[k] = extravertexBuffer
        indexBufferDict[k] = indexBuffer
    # for vB in vertexBufferDict.values():
        # print(vB)
    # for iB in indexBufferDict.values():
        # print(iB)
    materialList = []
    materialSlotNames = []
    for k, item in mergeData.items():
        for matId, material in enumerate(item["Materials"]):
            if not material in materialList:
                materialList.append(material)
                materialSlotNames.append(item["MaterialSlotNames"][matId])

    baseVertexIndex = 0
    baseIndexIndex = 0
    for matId, material in enumerate(materialList):
        subsetDict = {}
        #find subsets to material
        for k, item in mergeData.items():
            if material in item["Materials"]:
                subsetDict[k] = item["Subsets"]["data"][item["Materials"].index(material)]
        # print(subsetDict)
        #put all data of subset together
        mergeSubset = {"firstVertex" : str(baseVertexIndex),"numVertices": "0", "firstIndex":str(baseIndexIndex), "numIndices": "0"}
        if materialSlotNames[matId] is not None and materialSlotNames[matId] != "":
            mergeSubset["materialSlotName"] = materialSlotNames[matId]
        for k, subsets in subsetDict.items():
            numVertices = int(subsets["numVertices"])
            numIndices = int(subsets["numIndices"])
            vertexList = vertexBufferDict[k][int(subsets["firstVertex"]):int(subsets["firstVertex"])+numVertices]
            indexList = indexBufferDict[k][int(subsets["firstIndex"]):int(subsets["firstIndex"])+numIndices]
            minIndexList = min(indexList)
            indexList = [i-minIndexList+baseVertexIndex for i in indexList]   #normalize count to start by zero and apply offset
            # print("baseIndexIndex: {}, baseVertexIndex: {}, ".format(baseIndexIndex,baseVertexIndex))
            # print("index first: {}, num: {} \nindexList: {}".format(subsets["firstIndex"],int(subsets["firstIndex"])+numIndices,indexList))
            # print("vertex first: {}, num: {} \nvertexList: {}".format(subsets["firstVertex"],int(subsets["firstVertex"])+numVertices,vertexList))
            finalIndexBuffer+=indexList
            finalVertexBuffer+=vertexList
            if len(extravertexBufferDict[k]) > 0 : 
            	 finalExtraVertexBuffer += extravertexBufferDict[k][int(subsets["firstVertex"]):int(subsets["firstVertex"])+numVertices]
            
            mergeSubset["numVertices"] = "{}".format(int(mergeSubset["numVertices"]) + numVertices)
            mergeSubset["numIndices"] = "{}".format(int(mergeSubset["numIndices"]) + numIndices)
            baseVertexIndex += numVertices
            baseIndexIndex += numIndices

        finalSubsets.append(mergeSubset)
        finalMaterials.append(material)

    # print(finalMaterials)
    # for i in finalSubsets:
        # print("i:{}".format(i))
    # print("{} entries".format(len(finalIndexBuffer)))
    # print(finalIndexBuffer)
    # print("{} vertices".format(len(finalVertexBuffer)))
    # for i in finalVertexBuffer:
        # print("vertex: {}".format(i))
    #overwrite shapeData with final values

    if ("I3D_mergeChildren" in sceneNodeData):  #mergeChildren material behavior like maya exporter
        if len(finalMaterials) == 0:
            shapeData["Materials"] = ["default"]
        else:
            shapeData["Materials"] = [finalMaterials[0]]
    else:
        shapeData["Materials"] = finalMaterials
    shapeData["Subsets"]['data'] = finalSubsets
    shapeData["Subsets"]["count"] = str(len(finalSubsets))

    for i in range(0,len(finalIndexBuffer),3):
        finalTriangles.append({"vi" : "{} {} {}".format(finalIndexBuffer[i],finalIndexBuffer[i+1],finalIndexBuffer[i+2])})
    # print("finalTriangles: {}".format(finalTriangles))
    shapeData["Triangles"]['data'] = finalTriangles
    shapeData["Triangles"]['count'] = str(len(finalTriangles))
    shapeData["Vertices"]['data'] = finalVertexBuffer
    shapeData["Vertices"]['count'] = str(len(finalVertexBuffer))
    
    if len(finalExtraVertexBuffer) > 0 :
    	shapeData["Vertices"]['extraData'] = finalExtraVertexBuffer
    	shapeData["Vertices"]['extraDataFormats'] = extraFormats    
   
    
    #uvDensity
    if UIGetAttrBool("I3D_exportTexCoordsUVDensity"):
        for subset in finalSubsets:
            subset.update(i3d_densityUtil.computeUvDensity(shapeData["Triangles"]["data"],shapeData["Vertices"],int(subset["firstIndex"]),int(subset["numIndices"])))

    if ("I3D_mergeChildren" in sceneNodeData):  #mergeChildren
        if "dataFormats" not in shapeData["Vertices"]:shapeData["Vertices"]["dataFormats"] = {}

        shapeData["Vertices"]["dataFormats"]["generic"] = "true"
    else:
        if "dataFormats" not in shapeData["Vertices"]:shapeData["Vertices"]["dataFormats"] = {}
        
        shapeData["Vertices"]["dataFormats"]["singleblendweights"] = "true"


    return shapeData

def getMergeMemberShapeData(shapeNameStr, specialValue, rootStr, applyTrans, applyRot, applyScale):
    """
    Returns all data necessary to write the xml output file in the case the shape object is root of a merge group.
    vertices are transformed to root space.

	Note we do not process vertex animations in merge shapes.. we can in theory but it is alot of checking

    :param shapeNameStr: Name of the shape
    :param specialValue: the special value, dependent if it is called for a merge children or merge group
    :param rootStr: the name of the root object
    :returns: a dictionary with all necessary shape data
    """
    customShapeAttributes = None   
    shapeData = {}
    try:
        mesh = bpy.data.meshes[bpy.data.objects[shapeNameStr].data.name]
        shapeData["name"] = mesh.name

        if "customShapeAttributesFile" in mesh:
            customShapeAttributes = I3D_CustomShapeAttributes.load_from_xml(mesh["customShapeAttributesFile"])
    except:
        return None

    # --- generate exporting mesh
    meshOwners = getMeshOwners(bpy.data.objects[shapeNameStr].data.name)
    ownerObj = bpy.data.objects[meshOwners[0]]

    nodeVisible = isNodeVisible(ownerObj.name)
    if not nodeVisible:
        ownerObj.hide_set(False)

    for modifier in ownerObj.modifiers:  # cannot have skinning and merge shapes
        if modifier.type == 'ARMATURE':
            raise Exception("Cannot have armature and merge shapes within the same Object")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    for object_instance in depsgraph.object_instances:
        if (object_instance.object.name == ownerObj.name):            #operate on right object
            if(UIGetAttrString('I3D_exportApplyModifiers')):
                object_eval = object_instance.object.evaluated_get(depsgraph)
            else:
                object_eval = object_instance.object.original
            m_meshGen = bpy.data.meshes.new_from_object(object_eval, preserve_all_data_layers=True, depsgraph=depsgraph)
            break
    # -------------------------------------------------------------
    # --- calculate triangles and normals with applied modifiers
    m_meshGen.calc_loop_triangles()
    m_meshGen.calc_normals_split()
    #m_meshGen.calc_tangents()

    # if there is no mapping then lets create one 
    if customShapeAttributes == None: 
        customShapeAttributes = generate_custom_shape_attributes(m_meshGen, False)
        
    customShapeAttributes.validate(m_meshGen)

 
    # -------------------------------------------------------------
    # --- root -> member transformation
    if rootStr == 'ORIGIN':
        matrixTransform = mathutils.Matrix.Identity(4)
    else:
        l2 = bpy.data.objects[shapeNameStr].matrix_world
        l1 = bpy.data.objects[rootStr].matrix_world
        matrixTransform = l1.inverted() @ l2
        translation, rotationQuat, scale = matrixTransform.decompose()
        if applyTrans:
            translationMat = mathutils.Matrix.Translation(translation)
        else:
            translationMat = mathutils.Matrix.Translation((0.0, 0.0, 0.0))      #identity
        if applyRot:
            rotationMat = rotationQuat.to_matrix().to_4x4()
        else:
            rotationMat = mathutils.Matrix.Rotation(math.radians(0.0), 4, 'X')  #identity
        if applyScale:
            scaleMat = mathutils.Matrix.Diagonal(scale).to_4x4()
        else:
            scaleMat = mathutils.Matrix.Scale(1, 4)                             #identity
        matrixTransform = translationMat @ rotationMat @ scaleMat

    # -------------------------------------------------------------
    materialsList, materialSlotNames = getShapeMaterials(m_meshGen.name)
    m_materials = {}
    for mat in materialsList:
        m_materials[mat] = []
    if (len(materialsList) > 1):
        for m_triangle in m_meshGen.loop_triangles:
            m_mat = m_meshGen.materials[m_triangle.material_index]
            if None == m_mat:
                m_mat = "default"
            else:
                m_mat = m_mat.name
            m_materials[m_mat].append(m_triangle.index)



 
 
    m_vertices = {"data": []}
    m_triangles = {"data": []}
    m_subsets = {"data": []}

    # -------------------------------------------------------------
    bakeTransforms = "BAKE_TRANSFORMS" == UIGetAttrString('I3D_exportAxisOrientations')
 
    m_indexBuffer = {}
    m_currentIndex = 0
    m_firstIndex = 0
    m_numVerticesSet = set()
    m_trainglesCount = 0
    m_subsetsCount = 0
    m_counter = 0

    showAttributeWarning = True
    for matId, m_mat in enumerate(materialsList):
        m_matItem = m_materials[m_mat]
        m_trainglesCount += len(m_matItem)
        m_subsetsCount += 1
        m_numIndices = 0
        m_numVerticesSet.clear()
        for m_primIndex in m_matItem:
            m_triangle = m_meshGen.loop_triangles[m_primIndex]
            m_strVI = ''
            for m_loopIndex in m_triangle.loops:
                m_loop = m_meshGen.loops[m_loopIndex]
                m_vertexIndex = m_loop.vertex_index
                vertex = m_meshGen.vertices[m_vertexIndex]
                vertItem = customShapeAttributes.getVertexData(m_meshGen, vertex, m_loop, matrixTransform, bakeTransforms,showAttributeWarning)
                showAttributeWarning = False
                if type(specialValue) == float:
                    m_vertItem["data"]["g"] = "{:g}".format(specialValue)
                elif type(specialValue) == int:
                    m_vertItem["data"]["bi"] = "{:g}".format(specialValue)
                m_indexData = IndexBufferItem(vertItem,m_mat)
                if ( m_indexData not in m_indexBuffer ):
                    m_indexBuffer[ m_indexData ] = m_counter
                    m_counter += 1
                    append_vertex_item(m_vertItem,m_vertices)
                m_currentIndexVertex = m_indexBuffer[ m_indexData ]
                m_strVI  += " {:d}".format(m_currentIndexVertex)
                if ( 0 == m_numIndices ):
                    m_firstIndex = m_currentIndex
                m_numVerticesSet.add( m_currentIndexVertex )
                m_currentIndex += 1
                m_numIndices += 1
            m_triItem = {}
            m_triItem["vi"] = m_strVI.strip()
            m_triangles["data"].append(m_triItem)
        m_subsetItem = {}
        m_subsetItem["firstVertex"] = "{:g}".format(min(m_numVerticesSet))
        m_subsetItem["numVertices"] = "{:g}".format(len(m_numVerticesSet))
        m_subsetItem["firstIndex"]  = "{:g}".format(m_firstIndex)
        m_subsetItem["numIndices"]  = "{:g}".format(m_numIndices)
        if materialSlotNames[matId] != None:
            m_subsetItem["materialSlotName"] = materialSlotNames[matId]
        m_subsets["data"].append(m_subsetItem)
    
        
    customShapeAttributes.embedRuntimeFormats(m_vertices)
    
    m_vertices["count"]  = "{:g}".format(len(m_indexBuffer))
    m_triangles["count"] = "{:g}".format(m_trainglesCount)
    m_subsets["count"]   = "{:g}".format(m_subsetsCount)
    shapeData["Materials"] = materialsList
    shapeData["MaterialSlotNames"] = materialSlotNames
    shapeData["Vertices"] = m_vertices
    shapeData["Triangles"] = m_triangles
    shapeData["Subsets"] = m_subsets
    # --- Remove generated mesh
    VertexAttribute.cleanupTangentLayers(m_meshGen)
    bpy.data.meshes.remove(m_meshGen)
    if not nodeVisible:
        ownerObj.hide_set(True)

    VertexAttribute.clear_cache()

    return shapeData

def overrideBV(m_shapeStr,m_nodeData, m_sceneNodeData):
    if "boundingVolume" in m_sceneNodeData:
        bvCenterTarget, bvRadius = getBvCenterRadius(m_sceneNodeData["boundingVolume"])
        m_nodeData["bvCenter"] = "{:g} {:g} {:g}".format(bvCenterTarget.x,bvCenterTarget.y,bvCenterTarget.z)
        m_nodeData["bvRadius"] = "{:g}".format(bvRadius)

        # move bounding volume in target object's local space
        targetObj = bpy.data.objects[m_sceneNodeData["name"]]
        bvObj = bpy.data.objects[m_sceneNodeData["boundingVolume"]]

        # Get the transformation matrix from World Space to target object's  Local Space
        matrix_a_to_world = targetObj.matrix_world
        matrix_world_to_a = matrix_a_to_world.inverted()

        # Transform bounding volume from World Space to target object's Local Space
        matrix_b_to_a_local = matrix_world_to_a @ bvObj.matrix_world

        # Set bounding volume's matrix to the Local Space transformation matrix
        copyBV = bvObj.copy()
        copyBV.matrix_world = matrix_b_to_a_local

        bvCenterTarget, bvRadius = getBvCenterRadius(copyBV.name)
        m_nodeData["bvCenter"] = "{:g} {:g} {:g}".format(bvCenterTarget.x,bvCenterTarget.y,bvCenterTarget.z)
        m_nodeData["bvRadius"] = "{:g}".format(bvRadius)
        return True
    return False

def getShapeData(m_shapeStr, m_nodeData, m_sceneNodeData):
    """
    Returns all data necessary to write the xml output file in the case the shape object is root of a merge group.
    vertices are transformed to root space.

    :param m_shapeStr: Name of the shape
    :param m_nodeData: the dictionary for the return value
    :param m_sceneNodeData: the SceneNodeData with the detailed export settings
    :returns: a dictionary with all necessary shape data
    """
    if("mergeGroupMember" in m_sceneNodeData) or ("I3D_mergeChildren" in m_sceneNodeData):   #mergeGroupRoot or mergeChildren
        return getMergeGroupShapeData(m_shapeStr, m_nodeData, m_sceneNodeData)

    # override BV
    overrideBV(m_shapeStr, m_nodeData, m_sceneNodeData)

    m_mesh = bpy.data.meshes[m_shapeStr]
    m_nodeData["name"] = m_mesh.name
    meshOwners = getMeshOwners(m_shapeStr)
    m_obj = bpy.data.objects[meshOwners[0]]

    nodeVisible = isNodeVisible(m_obj.name)
    if not nodeVisible:
        m_obj.hide_set(False)
    # --- generate exporting mesh
    # original or without modifier and animation applied
    m_meshGen = getMeshFromDepsGraph(m_shapeStr)

    # -------------------------------------------------------------
    if ("I3D_cpuMesh" in m_sceneNodeData):
        m_nodeData["meshUsage"] = getMeshUsage(m_sceneNodeData["I3D_cpuMesh"])
    if "I3D_vertexCompressionRange" in m_sceneNodeData:
        m_nodeData['vertexCompressionRange'] = m_sceneNodeData['I3D_vertexCompressionRange']
    # -------------------------------------------------------------
    m_materialsList, m_materialSlotNames = getShapeMaterials(m_meshGen.name)
    m_materials = {}
    for m_mat in m_materialsList:
        m_materials[m_mat] = []
    # -------------------------------------------------------------
    # --- calculate triangles and normals with applied modifiers
    m_meshGen.calc_loop_triangles()
    m_meshGen.calc_normals_split()
    #m_meshGen.calc_tangents()

    # -------------------------------------------------------------
    if (len(m_materialsList) > 1):
        for m_triangle in m_meshGen.loop_triangles:
            m_mat = m_meshGen.materials[m_triangle.material_index]
            if None == m_mat:
                m_mat = "default"
            else:
                m_mat = m_mat.name
            m_materials[m_mat].append(m_triangle.index)
    else:
        for m_triangle in m_meshGen.loop_triangles:
            m_materials[m_materialsList[0]].append(m_triangle.index)

    # -------------------------------------------------------------
    m_vertices = {}
    m_triangles = {"data": []}
    m_subsets = {"data": []}

   #skinning
    m_nodeData["skinBindNodeIds"] = ""
    boneMap = {}
    hasSkinning = False
    for modifier in m_obj.modifiers:
        if modifier.type == 'ARMATURE' and modifier.object and UIGetAttrBool("I3D_exportSkinWeigths"):
            hasSkinning = True

            for group in bpy.data.objects[m_sceneNodeData['name']].vertex_groups:
                try:
                    UIShowWarning("skinning: group.index {0} name {1}".format(group.index, group.name))
                    boneMap[group.index] = m_sceneNodeData['bones'][group.name]     #assign bone nodeID to bone index
                except:
                    pass

            # 2021.05.17: not sure what _tail nodes were used for. all occurrences commented out...
            # #tailBone
            # for group in bpy.data.objects[m_sceneNodeData['name']].vertex_groups:
            #     try:
            #         newKey = sorted(boneMap.keys())[-1] + 1
            #         boneMap[newKey] = m_sceneNodeData['bones'][group.name+"_tail"] #tailbone
            #     except:
            #         pass

    for key in boneMap:
        m_nodeData["skinBindNodeIds"] = m_nodeData["skinBindNodeIds"] + str(boneMap[key])+ " "

    #GIANTS Editor cannot handle empty skinBindNodeIds
    if m_nodeData["skinBindNodeIds"] == "":
        del m_nodeData["skinBindNodeIds"]

    # -------------------------------------------------------------
    m_indexBuffer = {}
    m_currentIndex = 0
    m_firstIndex = 0
    m_numVerticesSet = set()
    m_trainglesCount = 0
    m_subsetsCount = 0
    m_counter = 0

    bakeTransforms = "BAKE_TRANSFORMS" == UIGetAttrString('I3D_exportAxisOrientations')

    customShapeAttributes = generate_custom_shape_attributes(m_meshGen, hasSkinning)

    if "customShapeAttributesFile" in m_mesh:
        filecustomShapeAttributes = I3D_CustomShapeAttributes.load_from_xml(m_mesh["customShapeAttributesFile"])
        if filecustomShapeAttributes != None:
            customShapeAttributes.merge(filecustomShapeAttributes)

   
    customShapeAttributes.validate(m_meshGen)

    showAttributeWarning = True
 
    # for vat animation
    # basically I am going to record the list of indices and do one frame for each anim at a time. 
    # I am doing like this to save processing a pile of memory. i.e sort out one target at a time
    vertexIndices = []
    loopIndices = []

    for matId, m_mat in enumerate(m_materialsList):
        m_matItem = m_materials[m_mat]
        m_trainglesCount += len(m_matItem)
        m_subsetsCount += 1
        m_numIndices = 0
        m_numVerticesSet.clear()
        for m_primIndex in m_matItem:
            m_triangle = m_meshGen.loop_triangles[m_primIndex]

            m_strVI = ''
            for m_loopIndex in m_triangle.loops:
                m_vertexIndex = m_meshGen.loops[m_loopIndex].vertex_index
                vertItem = customShapeAttributes.getVertexData(m_meshGen, m_meshGen.vertices[m_vertexIndex], m_meshGen.loops[m_loopIndex], None, bakeTransforms,showAttributeWarning)
                showAttributeWarning = False
                m_indexData = IndexBufferItem(vertItem, m_mat)
                if ( m_indexData not in m_indexBuffer ):
                    m_indexBuffer[m_indexData] = m_counter
                    append_vertex_item(vertItem,m_vertices)
                    vertexIndices.append(m_meshGen.vertices[m_vertexIndex])
                    loopIndices.append(m_meshGen.loops[m_loopIndex])
                    m_counter += 1
                m_currentIndexVertex = m_indexBuffer[m_indexData]
                m_strVI += " {:d}".format(m_currentIndexVertex)
                if ( 0 == m_numIndices ):
                    m_firstIndex = m_currentIndex
                m_numVerticesSet.add(m_currentIndexVertex)
                m_currentIndex += 1
                m_numIndices += 1
            m_triItem = {}
            m_triItem["vi"] = m_strVI.strip()
            m_triangles["data"].append(m_triItem)
        m_subsetItem = {}
        m_subsetItem["firstVertex"] = "{:g}".format(min(m_numVerticesSet))
        m_subsetItem["numVertices"] = "{:g}".format(len(m_numVerticesSet))
        m_subsetItem["firstIndex"] = "{:g}".format(m_firstIndex)
        m_subsetItem["numIndices"] = "{:g}".format(m_numIndices)
        if m_materialSlotNames[matId] != None:
            m_subsetItem["materialSlotName"] = m_materialSlotNames[matId]
        if UIGetAttrBool("I3D_exportTexCoordsUVDensity"):
            m_subsetItem.update(i3d_densityUtil.computeUvDensity(m_triangles["data"], m_vertices, m_firstIndex, m_numIndices))
        m_subsets["data"].append(m_subsetItem)


    
    customShapeAttributes.embedRuntimeFormats(m_vertices)

    m_vertices["count"] = "{:g}".format(len(m_indexBuffer))
    m_triangles["count"] = "{:g}".format(m_trainglesCount)
    m_subsets["count"] = "{:g}".format(m_subsetsCount)
    m_nodeData["Materials"] = m_materialsList
    m_nodeData["Vertices"] = m_vertices
    m_nodeData["Triangles"] = m_triangles
    m_nodeData["Subsets"] = m_subsets

    m_nodeData["VertexAnimations"] = customShapeAttributes.generateVertexAnimations(m_meshGen,m_mesh, vertexIndices, loopIndices, None, bakeTransforms)

    VertexAttribute.cleanupTangentLayers(m_meshGen)
    # --- Remove generated mesh
    if "isCopy" in m_meshGen and m_meshGen["isCopy"] == True:
        bpy.data.meshes.remove(m_meshGen)
    
   
    if not nodeVisible:
        m_obj.hide_set(True)

    VertexAttribute.clear_cache()

    return m_nodeData


def getRenderColorName(shapeStr):
    """
    Returns name of the Color Attributes set to be rendered

    :param shapeStr: string name from bpy.data.meshes

    """
    m_name = None
    try:
        m_mesh = bpy.data.meshes[shapeStr]
        m_colorLayerNames = m_mesh.color_attributes.keys()
        if (len(m_colorLayerNames)>0):
            m_index = m_mesh.color_attributes.render_color_index
            if ( -1!=m_index ):
                m_name = m_colorLayerNames[ m_index ]
    except:
        UIShowWarning("Blender version is lower than 3.2, vertex colors is not exported!")
    return m_name

def is_all_triangles(mesh):
    """Check if all faces in the mesh are triangles."""
    for face in mesh.polygons:
        if len(face.vertices) != 3:
            return False
    return True

def triangulate_mesh(mesh):
    if not is_all_triangles(mesh):
        # Create a bmesh from the mesh data
        bm = bmesh.new()
        bm.from_mesh(mesh)

        # Triangulate the bmesh
        bmesh.ops.triangulate(bm, faces=bm.faces[:])

        # Write the bmesh back to the mesh data
        bm.to_mesh(mesh)
        bm.free()


def getMeshFromDepsGraph(shapeStr):
    """
    Returns the Mesh from the depsgraph.

    If mod is false it returns the original object, otherwise the mesh with animation and modifiers applied
    """

    meshOwners = getMeshOwners(shapeStr)
    obj = bpy.data.objects[meshOwners[0]]
    depsgraph = bpy.context.evaluated_depsgraph_get()       #2.8 changes
    for object_instance in depsgraph.object_instances:
        # print("object_instance.object.name: " +object_instance.object.name +" obj.name: " + obj.name)
        if (object_instance.object.name == obj.name):            #operate on right object
            object_eval = object_instance.object.evaluated_get(depsgraph)
            
            # Access the evaluated mesh
            if object_eval.type == 'MESH':
                if UIGetAttrString('I3D_exportApplyModifiers'):
                    eval_mesh = object_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
                else :
                    eval_mesh = object_instance.object.original           #original, without modifier and animation applied
                if not is_all_triangles(eval_mesh):
                    print(f"Making copy of mesh {obj.name} as it is not triangulated; this will slow down the export")
                    meshGen = bpy.data.meshes.new_from_object(object_eval, preserve_all_data_layers=True, depsgraph=depsgraph)

                    # Create a temporary object to add shape keys
                    temp_obj = bpy.data.objects.new("TempObject", meshGen)

                    # Add the temporary object to a hidden collection to perform the shape key operations
                    hidden_collection = bpy.data.collections.new(name="HiddenCollection")
                    bpy.context.scene.collection.children.link(hidden_collection)
                    hidden_collection.objects.link(temp_obj)

                    # Ensure the new object has shape keys data block
                    if object_eval.data.shape_keys:
                        # Add the Basis shape key if it doesn't exist
                        if not temp_obj.data.shape_keys:
                            temp_obj.shape_key_add(name="Basis")

                        # Copy shape keys from the original object to the new object
                        for key_block in object_eval.data.shape_keys.key_blocks:
                            if key_block.name != "Basis":
                                new_shape_key = temp_obj.shape_key_add(name=key_block.name)
                                new_shape_key.data.foreach_set("co", [co for vert in key_block.data for co in vert.co])
                                new_shape_key.value = key_block.value

                    # Remove the temporary object and hidden collection after the shape keys are copied
                    hidden_collection.objects.unlink(temp_obj)
                    bpy.data.objects.remove(temp_obj)
                    bpy.data.collections.remove(hidden_collection)

                    triangulate_mesh(meshGen)
                    meshGen["isCopy"] = True
                else:
                    meshGen = eval_mesh

                return meshGen

            return meshGen
    return None

def getMeshUsage(isCpuMesh):
    if(isCpuMesh):
        return 256
    else:
        return 0

# this code walks through the items in a scene and establishes the objects that are owners of meshes. 
# the code is done to provide a cache of the owners as getMeshOwners is called all over the export routine and would 
# basically check each object over and over. 
gMeshOwnershipTable = {}
def clearMeshOwnershipTables():
    global gMeshOwnershipTable
    gMeshOwnershipTable = {}

def generateMeshOwnershipTables():
    global gMeshOwnershipTable
    clearMeshOwnershipTables()
    for m_obj in bpy.data.objects:
        if 'MESH' == m_obj.type:
            m_mesh = m_obj.data
            if m_mesh.name not in gMeshOwnershipTable:
                gMeshOwnershipTable[m_mesh.name] = []

            gMeshOwnershipTable[m_mesh.name].append(m_obj.name)    


def getMeshOwners(m_shapeStr):
    """ Returns a list of bpy.data.objects.name who have bpy.data.objects.data.name == m_shapeStr. """
    global gMeshOwnershipTable

    if m_shapeStr in gMeshOwnershipTable:
        return gMeshOwnershipTable[m_shapeStr]
    return []

def getBvCenterRadius(objStr):
    """ returns bvCenter and bvRadius of the mesh of a given object objStr is the name of an object with a mesh attached """

    m_mesh      = bpy.data.meshes[bpy.data.objects[objStr].data.name]
    m_vSum      = mathutils.Vector( (0,0,0) )
    m_bvRadius  = mathutils.Vector( (0,0,0) )
    m_vCount    = 0
    bVObjMat = bpy.data.objects[objStr].matrix_world
    if ( "BAKE_TRANSFORMS"  == UIGetAttrString('I3D_exportAxisOrientations')): #meshTransformation
        bVObjMat = bakeTransformMatrix(bVObjMat)

    for m_v in m_mesh.vertices:
        vertexWorld = bVObjMat @ m_v.co
        m_vSum += vertexWorld
        m_vCount    += 1
    m_bvCenter = m_vSum / m_vCount
    for m_v in m_mesh.vertices:
        vertexWorld = bVObjMat @ m_v.co
        m_vect      = m_bvCenter - vertexWorld
        m_bvRadius  = max( m_vect.length, m_bvRadius )
    return m_bvCenter, m_bvRadius

def getNurbsCurveData(m_shapeStr,m_nodeData):
    m_curve = bpy.data.curves[m_shapeStr]
    m_nodeData["name"] = m_curve.name
    m_nodeData["form"] = "open"
    if ( len( m_curve.splines ) ):
        m_spline = m_curve.splines[0]
        if m_spline.use_cyclic_u: m_nodeData["form"] = "closed"
        m_splinePoints = m_spline.points
        if ( "POLY"   == m_spline.type ):   m_splinePoints = m_spline.points
        if ( "NURBS"  == m_spline.type ):   m_splinePoints = m_spline.points
        if ( "BEZIER" == m_spline.type ):   m_splinePoints = m_spline.bezier_points
        if ( m_splinePoints ):
            m_points = []
            for m_p in m_splinePoints:
                m_pointCoords  = m_p.co.xyz[:]
                m_orient = UIGetAttrString('I3D_exportAxisOrientations')
                if ( "BAKE_TRANSFORMS"  == m_orient ): # x z -y
                    m_pointCoords = ( m_pointCoords[0], m_pointCoords[2], - m_pointCoords[1] )
                m_points.append( "{:g} {:g} {:g}".format(m_pointCoords[0],m_pointCoords[1],m_pointCoords[2]) )
            m_nodeData['points'] = m_points
    return m_nodeData

def getShapeMaterials(shapeStr):
    """ Returns a list of all material names related to the mesh object """

    materialIndexes = []
    m_materials = []
    m_materialSlotNames = []
    try:
        mesh = bpy.data.meshes[shapeStr]
        for triangle in mesh.loop_triangles:
            if ( triangle.material_index  not in materialIndexes ):
                materialIndexes.append( triangle.material_index )
        for matIndex in  materialIndexes:
            if mesh.materials:
                m_mat = mesh.materials[matIndex]
                if m_mat:
                    m_materials.append(m_mat.name)
                    if "materialSlotName" in m_mat:
                        m_materialSlotNames.append(m_mat["materialSlotName"])
                    else:
                        m_materialSlotNames.append(None)
                else:
                    if "default" not in m_materials:
                        m_materials.append("default")
                        m_materialSlotNames.append(None)
            else:
                if "default" not in m_materials:
                    m_materials.append("default")
                    m_materialSlotNames.append(None)
    except:
        # print(shapeStr + " is no mesh")
        if "default" not in m_materials:
            m_materials.append("default")
            m_materialSlotNames.append(None)
    return m_materials, m_materialSlotNames

def getMaterialFiles(materialStr):
    """ Returns a dictionary with a filepath assigned to a material """

    m_files = {}
    #2.8 update
    if materialStr in bpy.data.materials:
        mat = bpy.data.materials[materialStr]
        if "customShader" not in mat:
            if(mat.use_nodes):
                textures = [x for x in mat.node_tree.nodes if x.type=='TEX_IMAGE']
                for textureNode in textures:
                    image = textureNode.image
                    if(image):
                        m_files[os.path.normpath(bpy.path.abspath(image.filepath))] = getTextureTypeInSlot(mat, textureNode)
        shaderFileData = None
        if "customShader" in mat:
            #take shader location to put together an absolute path
            shaderFile = mat["customShader"]
            shaderFilePath = os.path.normpath(os.path.join(bpy.path.abspath("//"), shaderFile))
            if shaderFile.startswith("$"):
                shaderFilePath = shaderFile
            shaderFileData = i3d_shaderUtil.extractXMLShaderData(shaderFilePath)
            # shaderFilePath = os.path.dirname(shaderFile)

        shaderParamMappings = None
        if "customMappings" in mat:
             #take shader location to put together an absolute path
            mappingsFile = mat["customMappings"]
            mappingsFilePath = os.path.normpath(os.path.join(bpy.path.abspath("//"), shaderFile))
            if mappingsFile.startswith("$"):
                mappingsFilePath = mappingsFile
            shaderParamMappings = i3d_shaderUtil.extractXMLParamaterMappingData(mappingsFilePath)
   
        handledTextures = []
        handledBuffers = []
        # walk through the default textures 
        if shaderFileData :
            for key, defaulttextureinfo in shaderFileData["defaultTextures"].items():
                shadervalue = None
                # if the node name is the prefered route. 
                if "customParameter_preferDefaultTextureFromShaderNodeName" in mat and mat["customParameter_preferDefaultTextureFromShaderNodeName"] == "True":
                    shadervalue = i3d_shaderUtil.getMaterialShaderTextureParamFromNodeName(materialStr, defaulttextureinfo["nodename"])
                #if no value found look in the shader
                if shadervalue == None:
                    shadervalue = i3d_shaderUtil.getMaterialShaderTextureParamFromLinkInputNames(materialStr, defaulttextureinfo["inputlinks"])
            
                if shadervalue != None:
                    abspath = os.path.normpath(shadervalue)
                    if shadervalue in m_files:
                        UIShowWarning("texture already {0} already has key {1} trying to add for {2}".format(abspath, m_files[abspath], key))
                    else:
                        m_files[abspath] = key

            # now lets walk through the custom textures 
            searchforcustomtexturenode = shaderParamMappings != None and "customTexture_takeParamFromShaderNodeName" in mat and mat["customTexture_takeParamFromShaderNodeName"] == "True"
        
            customShaderVariation = None
            if "customShaderVariation" in mat:
                customShaderVariation = mat["customShaderVariation"]
                if customShaderVariation == "None":
                    customShaderVariation = None

            includeGroups = ["base"]
            if customShaderVariation != None:
                variation_groups_str = shaderFileData["variations_groups"][customShaderVariation]
                if variation_groups_str is not None:
                    includeGroups = variation_groups_str.split()

            for name , defaultstr in shaderFileData["textures"].items():
                texture_group = shaderFileData["textures_group"][name]
                if texture_group is None or texture_group not in includeGroups: 
                    continue
                # first see if the custom texture is overloaded in the material 
                textureName = "customTexture_" + name
                if textureName in mat :
                    if textureName in m_files:
                        UIShowWarning("texture already {0} already has key {1} trying to add for {2}".format(mat[textureName], m_files[mat[textureName]],textureName))
                    else:
                        m_files[textureName] = mat[textureName]
                    handledTextures.append(name)
                else:
                    if searchforcustomtexturenode != None and name in shaderParamMappings["textureblenderMaterialLinkDict"]: 
                        shadervalue = i3d_shaderUtil.getMaterialShaderTextureParamFromNodeName(materialStr, shaderParamMappings["textureblenderMaterialLinkDict"][name])
                        if shadervalue != None:
                            if textureName in m_files:
                                UIShowWarning("2. texture already {0} already has key {1} trying to add for {2}".format(shadervalue, m_files[shadervalue], textureName))
                            else:
                                m_files[textureName] = shadervalue
                            handledTextures.append(name)

            # custom buffers
            searchforcustombuffernode = shaderParamMappings != None and "customBuffer_takeParamFromShaderNodeName" in mat and mat["customBuffer_takeParamFromShaderNodeName"] == "True"

            for name , defaultstr in shaderFileData["buffers"].items():
                buffer_group = shaderFileData["buffers_group"][name]
                if buffer_group is None or buffer_group not in includeGroups: 
                    continue
                # first see if the custom buffer is overloaded in the material 
                bufferName = "customBuffer_" + name
                if bufferName in mat :
                    if bufferName in m_files:
                        UIShowWarning("buffer already {0} already has key {1} trying to add for {2}".format(mat[bufferName], m_files[mat[bufferName]],bufferName))
                    else:
                        m_files[bufferName] = mat[bufferName]
                    handledBuffers.append(name)
                else:
                    if searchforcustombuffernode != None and name in shaderParamMappings["bufferblenderMaterialLinkDict"]: 
                        shadervalue = i3d_shaderUtil.getMaterialShaderBufferParamFromNodeName(materialStr, shaderParamMappings["bufferblenderMaterialLinkDict"][name])
                        if shadervalue != None:
                            if bufferName in m_files:
                                UIShowWarning("2. buffer already {0} already has key {1} trying to add for {2}".format(shadervalue, m_files[shadervalue], bufferName))
                            else:
                                m_files[bufferName] = shadervalue
                            handledBuffers.append(name)

        for key in mat.keys():
            m_str = "{}".format(key)
            if ( "customShader" == m_str ):
                absPath = shaderFilePath.replace(os.sep, "/")
                m_files[absPath] = "customShader"

# this is handled above
#            elif ( 0 == m_str.find("customTexture_") ):
#                # weird path behavior -> evgen 05.06.2020
#                # absPath = os.path.normpath(shaderFilePath + "\\" + mat[m_str])
#                absPath = os.path.splitext(bpy.data.filepath)[0].rsplit("\\",1)[0] +"\\" + mat[m_str]
#                if mat[m_str].startswith("$"):
#                    absPath = mat[m_str]
#                m_files[absPath] = m_str
#                handledTextures.append(m_str.split("_")[1])
        
        # Add textures selected through a parameter template and not overriden by a user-defined value.
        if shaderFileData is not None and "parameterTemplates" in shaderFileData:
            for parameterTemplateId, parameterTemplate in shaderFileData["parameterTemplates"].items():
                selectedParentSubTemplateId = None
                subTemplateId = parameterTemplate["rootSubTemplateId"]
                while subTemplateId is not None:
                    subTemplate = parameterTemplate["subtemplates"][subTemplateId]
                    parentSubTemplateId = subTemplate["parentId"]

                    subTemplateKey = "customParameterTemplate_{}_{}".format(parameterTemplateId, subTemplateId)
                    selectedSubTemplateId = None
                    if subTemplateKey in mat:
                        selectedSubTemplateId = mat[subTemplateKey]
                    elif selectedParentSubTemplateId is not None:
                        selectedSubTemplateId = selectedParentSubTemplateId

                    if selectedSubTemplateId is not None:
                        selectedSubTemplate = subTemplate["templates"][selectedSubTemplateId]
                        for textureName, _ in parameterTemplate["textures"].items():
                            if textureName not in handledTextures and textureName in selectedSubTemplate:
                                m_files[selectedSubTemplate[textureName]] = "customTexture_{}".format(textureName)
                                handledTextures.append(textureName)

                        if "parentTemplate" in selectedSubTemplateId:
                            selectedParentSubTemplateId = selectedSubTemplateId["parentTemplate"]
                        else:
                            selectedParentSubTemplateId = subTemplate["defaultParentTemplate"]

                    subTemplateId = parentSubTemplateId
    return m_files

def getTextureTypeInSlot( mat, textureNode ):
    """ Checks on which input slot the texture is mapped and returns type accordingly """

    #maybe solid recursive search necessary..
    if(mat.use_nodes):
        #check for values in immediate connected node -> add search to check further down in the hierarchy
        surfaceNode = mat.node_tree.nodes['Material Output'].inputs['Surface'].links[0].from_node

        if 'Specular' in surfaceNode.inputs and surfaceNode.inputs['Specular'].is_linked:
            for links in surfaceNode.inputs['Specular'].links:
                if(links.from_node == textureNode):
                    return "Glossmap"
        # In Blender 4.0, the link changed to "Specular IOR Level" instead of just "Specular".
        if 'Specular IOR Level' in surfaceNode.inputs and surfaceNode.inputs['Specular IOR Level'].is_linked:
            for links in surfaceNode.inputs['Specular IOR Level'].links:
                if(links.from_node == textureNode):
                    return "Glossmap"
        if 'Roughness' in surfaceNode.inputs and surfaceNode.inputs['Roughness'].is_linked:
            for links in surfaceNode.inputs['Roughness'].links:
                if(links.from_node == textureNode):
                    return "Glossmap"
        if 'Base Color' in surfaceNode.inputs and surfaceNode.inputs['Base Color'].is_linked:
            for links in surfaceNode.inputs['Base Color'].links:
                if(links.from_node == textureNode):
                    return "Texture"
        if 'Normal' in surfaceNode.inputs and surfaceNode.inputs['Normal'].is_linked:
            for links in surfaceNode.inputs['Normal'].links:
                if(links.from_node == textureNode):
                    return "Normalmap"
                elif(links.from_node.type == 'NORMAL_MAP'):
                    normalMapNode = links.from_node
                    if 'Color' in normalMapNode.inputs and normalMapNode.inputs['Color'].is_linked:
                        for linksNormalMap in normalMapNode.inputs['Color'].links:
                            if(linksNormalMap.from_node == textureNode):
                                return "Normalmap"
        if 'Emission' in surfaceNode.inputs and surfaceNode.inputs['Emission'].is_linked:
            for links in surfaceNode.inputs['Emission'].links:
                if(links.from_node == textureNode):
                    return "Emissivemap"
    return "Texture"

def getNormalMapStrength(mat):
    """ gets the strength of the normal map from the normal map node """
    if(mat.use_nodes):
        surfaceNode = mat.node_tree.nodes['Material Output'].inputs['Surface'].links[0].from_node
        if 'Normal' in surfaceNode.inputs and surfaceNode.inputs['Normal'].is_linked:
            return surfaceNode.inputs['Normal'].links[0].from_node.inputs['Strength'].default_value

def getShapeNode(nodeData):
    """ Returns bpy.data.objects[nodeStr].data.name """

    if "I3D_mergeChildren" in nodeData:
        return nodeData["fullPathName"]
    nodeStr = nodeData["fullPathName"]
    if nodeStr in bpy.data.objects:
        obj = bpy.data.objects[nodeStr]
        return obj.data.name
    else:
        if ("fullPathNameOrig" in nodeData):
            nodeStr = nodeData["fullPathNameOrig"]
            if nodeStr in bpy.data.objects:
                obj = bpy.data.objects[nodeStr]
                return obj.data.name
    return None

def getNodeType(nodeStr):
    """ Returns the correspondent type """

    nodeObj = bpy.data.objects[nodeStr]
    nodeTypeStr = nodeObj.type
    if ('EMPTY'  == nodeTypeStr):
        return 'TYPE_TRANSFORM_GROUP'
    if ('LIGHT'   == nodeTypeStr):
        return 'TYPE_LIGHT'
    if ('CAMERA' == nodeTypeStr):
        return 'TYPE_CAMERA'
    if ('CURVE'  == nodeTypeStr):
        return 'TYPE_NURBS_CURVE'
    if ('MESH'   == nodeTypeStr):
        return 'TYPE_MESH'
    return 'TYPE_TRANSFORM_GROUP'

def bakeTransformMatrix(matrix):
    rotation_minus90_x = np.array([
        [1, 0, 0, 0],
        [0, 0, 1, 0],
        [0, -1, 0, 0],
        [0, 0, 0, 1]
    ])
    rotation_plus90_x = np.array([
        [1, 0, 0, 0],
        [0, 0, -1, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1]
    ])
    return mathutils.Matrix(rotation_minus90_x.tolist()) @ matrix @ mathutils.Matrix(rotation_plus90_x.tolist())

def getNodeTranslationRotationScale(nodeStr):
    """ Returns the Transformation of the nodes """

    node = bpy.data.objects[nodeStr]
    orient = UIGetAttrString('I3D_exportAxisOrientations')
    if ( "BAKE_TRANSFORMS"  == orient ):
        # transform matrix Blender -> OpenGL
        m_matrix = bakeTransformMatrix( node.matrix_local )
        if ( "CAMERA"  ==  node.type or "LIGHT"  ==  node.type ):
            m_matrix = m_matrix @ mathutils.Matrix.Rotation( math.radians( -90 ), 4, "X" )
        if ( node.parent ):
            if ( "CAMERA"  ==  node.parent.type or "LIGHT"  ==  node.parent.type ):
                m_matrix = mathutils.Matrix.Rotation( math.radians( 90 ), 4, "X" ) @ m_matrix
    elif ( "KEEP_TRANSFORMS"  == orient ):
        m_matrix        = node.matrix_local
    m_translation   = m_matrix.to_translation()[:]
    m_rotation      = m_matrix.to_euler( "XYZ" )
    m_rotation      = ( math.degrees( m_rotation.x ),
                        math.degrees( m_rotation.y ),
                        math.degrees( m_rotation.z ) )
    m_scale         = m_matrix.to_scale()[:]
    m_translation  = "%g %g %g" %( m_translation )
    m_rotation     = "%g %g %g" %( m_rotation  )
    m_scale        = "%g %g %g" %( m_scale )
    return ( m_translation, m_rotation, m_scale )

def getRootBoneName(boneStr,armStr):
    """ Returns the bone name of the root bone of the given bone """

    boneObj = bpy.data.objects[armStr].data.bones[boneStr]
    while boneObj.parent:
        boneObj = boneObj.parent
    return boneObj.name

def updateNodeTransformation(nodeStr, boneStr, armatureStr):
    """ Adjusts the transformation of the bone in respect to the node it belongs to"""

    nodeObj = bpy.data.objects[nodeStr]
    boneObj = bpy.data.objects[armatureStr].data.bones[boneStr]
    rootBoneObj = bpy.data.objects[armatureStr].data.bones[getRootBoneName(boneStr,armatureStr)]
    if ( "BAKE_TRANSFORMS"  == UIGetAttrString('I3D_exportAxisOrientations')): #meshTransformation
        objMat = bakeTransformMatrix( nodeObj.matrix_local )
        rootBoneMat = bakeTransformMatrix( rootBoneObj.matrix_local )
        boneMat = bakeTransformMatrix(boneObj.matrix_local)
        # b0 = rootBoneMat
        # b1 = boneMat
        # m1 = objMat
        # l0 = b0
        # l1 = l0.inverted() @ b1
        # l2 = l1.inverted() @ l0.inverted() @ m1
        # matrix = l2
        matrix = (rootBoneMat.inverted() @ boneMat).inverted() @ rootBoneMat.inverted() @ objMat
    else:
        objMat = nodeObj.matrix_local
        rootBoneMat = rootBoneObj.matrix_local
        boneMat = boneObj.matrix_local
        matrix = (rootBoneMat.inverted() @ boneMat).inverted() @ rootBoneMat.inverted() @ objMat

    translation   = matrix.to_translation()[:]
    rotation      = matrix.to_euler( "XYZ" )
    rotation      = ( math.degrees( rotation.x ), math.degrees( rotation.y ), math.degrees( rotation.z ) )
    scale         = matrix.to_scale()[:]
    translation  = "%g %g %g" %( translation )
    rotation     = "%g %g %g" %( rotation  )
    scale        = "%g %g %g" %( scale )
    return ( translation, rotation, scale )

def getBoneTranslationRotationScale(boneStr,armStr):
    """
    Calculates translation, rotation and scale for the bone.

    :param boneStr: name of bone
    :param armStr: name of the armature that the bone belongs to
    """

    boneObj = bpy.data.objects[armStr].data.bones[boneStr]
    parentObj = boneObj.parent
    if ( "BAKE_TRANSFORMS"  == UIGetAttrString('I3D_exportAxisOrientations') ):
        if(parentObj == None):  #isRootBone
            #transform to bone SPACE and apply axis transformation, but keep rotation
            matrix= bakeTransformMatrix(boneObj.matrix_local)
        else:
            l2 = bakeTransformMatrix(boneObj.matrix_local)
            l1 = bakeTransformMatrix(parentObj.matrix_local)
            matrix = l1.inverted() @ l2
    else:
        if(parentObj == None):
            matrix = boneObj.matrix_local
        else:
            matrix = parentObj.matrix_local.inverted() @ boneObj.matrix_local
    translation   = matrix.to_translation()[:]
    rotation      = matrix.to_euler( "XYZ" )
    rotation      = ( math.degrees( rotation.x ),
                        math.degrees( rotation.y ),
                        math.degrees( rotation.z ) )
    scale          = matrix.to_scale()[:]
    translation  = "%g %g %g" %( translation )
    rotation     = "%g %g %g" %( rotation  )
    scale         = "%g %g %g" %( scale  )
    return ( translation, rotation, scale  )

def getBoneTailTranslation(boneStr,armStr):
    """ Calculates the bone tail translation """

    if ( "BAKE_TRANSFORMS"  == UIGetAttrString('I3D_exportAxisOrientations') ):
        return "%g %g %g" %(0,0,- bpy.data.objects[armStr].data.bones[boneStr].length*bpy.data.objects[armStr].data.bones[boneStr].matrix_local.to_scale()[1]) #x z -y
    else:
        return "%g %g %g" %(0,bpy.data.objects[armStr].data.bones[boneStr].length*bpy.data.objects[armStr].data.bones[boneStr].matrix_local.to_scale()[1],0) #x z -y

def getKeyframePointsLocationRotation(keyframeStr,rootStr,actionStr):
    """ Returns dictionary of global transformation matrices keyed with timestamps """

    if isType(rootStr, "ARMATURE"):  #armature
        armStr = rootStr
        boneStr = keyframeStr

        isTailBone = False
        if(boneStr.split("_")[-1] == "tail"):
            isTailBone = True
            boneStr = boneStr[:-5]

        timestamps = []
        #get all timestamps for the bone's keyframes
        for group in bpy.data.actions[actionStr].groups:
            if group.name == boneStr:  #group to bone
                for fcrv in group.channels:
                    for kfp in fcrv.keyframe_points:
                        if not(kfp.co.x in timestamps):
                            timestamps.append(kfp.co.x)

        KeyframeDataPoints = {}
        sumInterpolationData =  []
        if(isTailBone):     #TailBone case
            for timestamp in timestamps:
                KeyframeDataPoints[timestamp] = {}
                matrixData, interpolation = getTailBoneKeyframePoint(timestamp,boneStr,armStr,actionStr)
                KeyframeDataPoints[timestamp]["matrixData"] = matrixData
                # KeyframeDataPoints[timestamp]["interpolationData"] = interpolation
                sumInterpolationData.append(interpolation)
            overallInterpolationData = {}
            for index in range(len(sumInterpolationData)):
                for key, value in sumInterpolationData[index].items():
                    if key in overallInterpolationData.keys():
                        continue
                overallInterpolationData[key] = value
            for timestamp in timestamps:
                KeyframeDataPoints[timestamp]["interpolationData"] = overallInterpolationData

            return KeyframeDataPoints
        sumInterpolationData =  []
        for timestamp in timestamps: #loop timestamps
            KeyframeDataPoints[timestamp] = {}
            animationDelta, interpolationData = getDataMatrixFormKeyframes(timestamp,boneStr,actionStr) #change Data   #local transform
            boneObj = bpy.data.objects[armStr].data.bones[boneStr]
            parentObj = boneObj.parent
            if ( "BAKE_TRANSFORMS"  == UIGetAttrString('I3D_exportAxisOrientations') ):
                if(boneObj.parent == None): #rootBone is in armature space
                    t1 = bakeTransformMatrix(animationDelta)
                    m1 = bakeTransformMatrix(boneObj.matrix_local)
                    matrixData = m1 @ t1
                else:   #bone is in parentBone Space
                    t2 = bakeTransformMatrix(animationDelta)
                    m2 = bakeTransformMatrix(boneObj.matrix_local)
                    l1 = bakeTransformMatrix(parentObj.matrix_local)
                    matrixData = l1.inverted() @ m2 @ t2
            else:
                if(boneObj.parent == None): #rootBone is in armature space
                    t1 = animationDelta
                    m1 = boneObj.matrix_local
                    matrixData = m1 @ t1
                else:   #bone is in parentBone Space
                    t2 = animationDelta
                    m2 = boneObj.matrix_local
                    l1 = parentObj.matrix_local
                    matrixData = l1.inverted() @ m2 @ t2
            KeyframeDataPoints[timestamp]["matrixData"] = matrixData #<- rotation and translation
            # KeyframeDataPoints[timestamp]["interpolationData"] = interpolationData
            sumInterpolationData.append(interpolationData)
        overallInterpolationData = {}
        for index in range(len(sumInterpolationData)):
            for key, value in sumInterpolationData[index].items():
                if key in overallInterpolationData.keys():
                    continue
                overallInterpolationData[key] = value

        for timestamp in timestamps: #loop timestamps
            KeyframeDataPoints[timestamp]["interpolationData"] = overallInterpolationData
        # returns a dict with the finished global transformed data per [timestamp] as key
        # for I3DKeyframe -> self._I3DKeyframePoints
        return KeyframeDataPoints
    else:
        timestamps = []
        #get all timestamps for the bone's keyframes
        for group in bpy.data.actions[actionStr].groups:    #should only contain single group
            groupName = group.name
            for fcrv in group.channels:
                for kfp in fcrv.keyframe_points:
                    if not(kfp.co.x in timestamps):
                        timestamps.append(kfp.co.x)
        KeyframeDataPoints = {}
        sumInterpolationData =  []
        for timestamp in timestamps: #loop timestamps
            KeyframeDataPoints[timestamp] = {}
            animationDelta, interpolationData = getDataMatrixFormKeyframes(timestamp,groupName,actionStr) #change Data   #local transform
            rootObj = bpy.data.objects[rootStr]
            parentObj = rootObj.parent
            if ( "BAKE_TRANSFORMS"  == UIGetAttrString('I3D_exportAxisOrientations')):
                if(parentObj == None):#parenting
                    matrixData = bakeTransformMatrix(animationDelta)
                    #AW 19/07/24 - fix for exporting animated cameras
                    if ( isType(rootStr, "CAMERA") ):
                        matrixData = matrixData @ mathutils.Matrix.Rotation( math.radians( -90 ), 4, "X" )
                else:
                    t1 = bakeTransformMatrix(animationDelta)
                    #AW 19/07/24 - fix for exporting animated cameras
                    if ( isType(rootStr, "CAMERA") ):
                        t1 = t1 @ mathutils.Matrix.Rotation( math.radians( -90 ), 4, "X" )

                    m1 =bakeTransformMatrix(parentObj.matrix_local)
                    matrixData = m1.inverted() @ t1
            else:
                if(parentObj == None):#parenting
                    matrixData = animationDelta
                else:
                    t1 = animationDelta
                    m1 = parentObj.matrix_local
                    matrixData = m1.inverted() @ t1
            KeyframeDataPoints[timestamp]["matrixData"] = matrixData #<- rotation and translation
            # KeyframeDataPoints[timestamp]["interpolationData"] = interpolationData
            sumInterpolationData.append(interpolationData)
        overallInterpolationData = {}
        for index in range(len(sumInterpolationData)):
            for key, value in sumInterpolationData[index].items():
                if key in overallInterpolationData.keys():
                    continue
                overallInterpolationData[key] = value

        for timestamp in timestamps: #loop timestamps
            KeyframeDataPoints[timestamp]["interpolationData"] = overallInterpolationData
        return KeyframeDataPoints

def getTailBoneKeyframePoint(timestamp,boneStr,armStr,actionStr):
    """ Return length * y-scale of bone in matrix form. """

    length = bpy.data.objects[armStr].data.bones[boneStr].length
    scale = [0,0,1] #default
    interpolation = {}
    for group in bpy.data.actions[actionStr].groups:
        if group.name == boneStr:  #group to bone
            for fcrv in group.channels:
                for kfp in fcrv.keyframe_points:
                    if(kfp.co.x == timestamp):
                        data = kfp.co.y
                        if("scale" in fcrv.data_path):
                            scale[fcrv.array_index] = data
                        interpolation[fcrv.data_path.split(".")[-1]] = kfp.interpolation    #get interpolation
    matrix = mathutils.Matrix.Translation((0,0,-(length*scale[1]))) @ mathutils.Euler((0,0,0)).to_matrix().to_4x4()
    return matrix, interpolation

def getDataMatrixFormKeyframes(timestamp, groupStr, actionStr): #T = Location@Rotation
    """ Return local Transformation, Location @ Rotation. """

    #Data Extraction
    location = [0,0,0]
    rotation = [0,0,0,0]
    scale = [1,1,1]
    interpolation = {}
    hasQuaternion = False

    for group in bpy.data.actions[actionStr].groups:
        if group.name == groupStr:  #group to bone
            for fcrv in group.channels:
                for kfp in fcrv.keyframe_points:

                    data = kfp.co.y
                    if("location" in fcrv.data_path):    #get rotation
                        location[fcrv.array_index] = data
                    elif("rotation" in fcrv.data_path):  #get location
                        if("quaternion" in fcrv.data_path):
                            hasQuaternion = True
                        rotation[fcrv.array_index] = data
                    elif("scale" in fcrv.data_path):      #get scale
                        scale[fcrv.array_index] = data
                    interpolation[fcrv.data_path.split(".")[-1]] = kfp.interpolation    #get interpolation
                    if(kfp.co.x >= timestamp):
                        break
    if(hasQuaternion):  #quaternion
        rotation = quaternionToEulerFormat(rotation)
    scaleMat = mathutils.Matrix.Scale(scale[0],4,(1,0,0)) @ mathutils.Matrix.Scale(scale[1],4,(0,1,0)) @ mathutils.Matrix.Scale(scale[2],4,(0,0,1))
    matrix =  mathutils.Matrix.Translation((location[0],location[1],location[2])) @ mathutils.Euler((rotation[0],rotation[1],rotation[2])).to_matrix().to_4x4() @ scaleMat    #scale @ location@rotation
    return matrix, interpolation

def formatKeyframePointData(timestamp,data):
    """ Return dictionary with formatted strings of the data """

    # interpolationMap = { "BEZIER": "bezier", "LINEAR": "linear"} #correct mapping GE-Blender
    formatData = {}
    formatData['time'] = timestamp * getFps()
    if "matrixData" in data:
        matrix = data["matrixData"]
        translation   = matrix.to_translation()[:]
        rotation      = matrix.to_euler( "XYZ" )
        rotation      = ( math.degrees( rotation.x ),
                            math.degrees( rotation.y ),
                            math.degrees( rotation.z ) )
        scale = matrix.to_scale()[:]
        if "interpolationData" in data:     #is always exported "linear"
            interpolation = data["interpolationData"]
            if("location" in interpolation):
                formatData['translation']  = "%g %g %g" %( translation )
                formatData['iptin'] = "linear"
                formatData['iptout'] = "linear"
                # formatData['iptin'] = interpolation["location"]
                # formatData['iptout'] = interpolation["location"]
            if("rotation_quaternion" in interpolation):
                formatData['rotation'] = "%g %g %g" %( rotation  )
                formatData['iprin'] = "linear"
                formatData['iprout'] = "linear"
                # formatData['iprin'] = interpolation["rotation_quaternion"]
                # formatData['iprout'] = interpolation["rotation_quaternion"]
            elif("rotation_euler" in interpolation):
                formatData['rotation'] = "%g %g %g" %( rotation  )
                formatData['iprin'] = "linear"
                formatData['iprout'] = "linear"
                # formatData['iprin'] = interpolation["rotation_euler"]
                # formatData['iprout'] = interpolation["rotation_euler"]
            if "scale" in interpolation:
                formatData['scale'] = "%g %g %g" %( scale)
                formatData['ipsin'] = "linear"
                formatData['ipsout'] = "linear"
    return formatData

def isNodeVisible(m_nodeStr):
    m_node = bpy.data.objects[m_nodeStr]
    return m_node.visible_in_viewport_get(bpy.context.space_data)


def is_really_absolute(path):
    """
    Determines if a path is truly absolute.
    For Windows, checks if the path starts with a drive letter.
    For Unix, checks if the path starts with a forward slash.
    For Blender, checks if the path starts with '//' indicating a relative path.
    """
    # Blender specific check for relative paths
    if path.startswith("//"):
        return False
    
    # Check for Windows-style absolute path (e.g., "C:\\path\\to\\file")
    if os.name == 'nt':  # nt means Windows
        return bool(os.path.splitdrive(path)[0])
    else:  # Unix-like systems
        return path.startswith("/")

def generate_crc(file_path):
    # Read the contents of the file
    if os.path.isfile(file_path):
        with open(file_path, 'rb') as f:
            file_contents = f.read()

        return hashlib.md5(file_contents).hexdigest()

    return -1

def getFileData(pathStr,data):
    """
    Configurates the data path

    If pathStr is relative, it is assumed that it is relative to the blender file,
    which is not necessarily true, thus pathStr should be an absolute path

    :param pathStr: for proper functionality, this is expected to be the absolute path to be configured
    :param data: container dictionary for the return data
    :returns: the dictionary data with "relativePath" and "filename" set
    """
    if pathStr.startswith("$"):
        data["relativePath"] = "true"
        data["filename"] = pathStr
        return data

    blendPath = os.path.dirname(bpy.data.filepath)
    #set absolute paths
    data["relativePath"] = "false"
    path = pathStr
    #put abspath differently together -> blender path as this is where the scene is and all the paths are coming from. 
    if not is_really_absolute(path):
        path = path.replace("//" , "\\")
        if path.startswith("\\"):
            path = path.lstrip("\\")
        path = os.path.join(blendPath, path)
    
    path = os.path.normpath(path)
  
    if UIGetAttrBool('I3D_UIexportCopyFiles') :
            # no copy needed as the file is in the same place 
        if UIGetAttrBool('I3D_exportUseSoftwareFileName'):
                exportfileLocation = blendPath
        else :
            exportfileLocation = os.path.dirname(bpy.path.abspath(bpy.context.scene.I3D_UIexportSettings.I3D_exportFileLocation))
            if not exportfileLocation or len(exportfileLocation) == 0 :
                UIShowWarning("can not save relative path using the filelocation as it is empty")
            else : # lets try copying 
                sourcepath = path
                targetpath = os.path.relpath(path,blendPath)
                targetpath = os.path.join(exportfileLocation, targetpath)
                targetpath = os.path.normpath(targetpath)
                if sourcepath != targetpath :
                    sourceCrc = generate_crc(sourcepath)
                    targetCrc = generate_crc(targetpath)
                    if sourceCrc != targetCrc : 
                        try:
                            print("copying: {} ({}) to {} ({})".format(sourcepath,sourceCrc,targetpath,targetCrc))
                              # Extract the directory from the target path
                            target_dir = os.path.dirname(targetpath)
    
                            # Create the target directory and any necessary parent directories if they don't exist
                            if not os.path.exists(target_dir):
                                os.makedirs(target_dir)
                            # Copy the file
                            shutil.copy(sourcepath, targetpath)

                        except Exception as e:
                            print(f"Error copying file: {e}")
                    else : 
                        print("crc matches  {} ({}) to {} ({})".format(sourcepath,sourceCrc,targetpath,targetCrc))
                    path = targetpath
                else : 
                    print("source and target files the same: {} ".format(sourcepath))

    isGameRelativePathSet = False 
    if UIGetAttrBool('I3D_exportGameRelativePath') :
        #load game relative paths
        gamePath = UIGetAttrString('I3D_gameLocation')
        if os.path.isdir("{}/bin/".format(gamePath)):
            gamePath = "{}/bin/".format(gamePath)
        if gamePath == "" and dirf.isWindows():
            gamePath = dirf.findFS22Path()
        #possible if gamepath is relative?
        if path.startswith(gamePath):
            data["relativePath"] = "true"
            path = os.path.relpath(path,gamePath)
            path = "$"+path
            isGameRelativePathSet = True

    if UIGetAttrBool('I3D_exportRelativePaths') and not isGameRelativePathSet:
        #load relative paths
        if UIGetAttrBool('I3D_exportUseSoftwareFileName'):
                data["relativePath"] = "true"
                exportfileLocation = blendPath
                exportfileLocation = os.path.normpath(exportfileLocation)
                path = os.path.relpath(path,exportfileLocation)
        else :
            exportfileLocation = os.path.dirname(bpy.path.abspath(bpy.context.scene.I3D_UIexportSettings.I3D_exportFileLocation))
            exportfileLocation = os.path.normpath(exportfileLocation)
            if not exportfileLocation or len(exportfileLocation) == 0 :
                data["relativePath"] = "false"
                UIShowWarning("can not save relative path using the filelocation as it is empty")
            else:
               data["relativePath"] = "true"
               path = os.path.relpath(path,exportfileLocation)

 
    path = os.path.normpath(path)   #clean up path
    path = path.replace( "\\","/")
    # print(path)
    data["filename"] = path
    return data

def getMaterialData(m_nodeStr, m_data):
    """ Configure  export parameters according to the material properties """

    if m_nodeStr in bpy.data.materials:
        m_mat = bpy.data.materials[m_nodeStr]
        m_data["name"] = m_mat.name

        ## double sided or not
        #m_data["doubleSided"] = "false" if m_mat.use_backface_culling else "true"
        #default values
        diffuseColorRed = m_mat.diffuse_color[0]
        diffuseColorGreen = m_mat.diffuse_color[1]
        diffuseColorBlue = m_mat.diffuse_color[2]

        smoothness = 1- m_mat.roughness
        specularIntensity = m_mat.specular_intensity
        metallic = m_mat.metallic

        if(m_mat.use_nodes):
            if len(m_mat.node_tree.nodes['Material Output'].inputs['Surface'].links) == 0 :
               UIShowError(f"Failed to find Material Output Surface output links on material `{m_mat.name}`") 

            #check for values in immediate connected node -> add search to check further down in the hierarchy
            surfaceNode = m_mat.node_tree.nodes['Material Output'].inputs['Surface'].links[0].from_node

            if "Base Color" in surfaceNode.inputs:
                # if surfaceNode.inputs["Base Color"].is_linked:
                diffuseColorRed = surfaceNode.inputs["Base Color"].default_value[0]
                diffuseColorGreen = surfaceNode.inputs["Base Color"].default_value[1]
                diffuseColorBlue = surfaceNode.inputs["Base Color"].default_value[2]
            elif "Color" in surfaceNode.inputs:
                diffuseColorRed = surfaceNode.inputs["Color"].default_value[0]
                diffuseColorGreen = surfaceNode.inputs["Color"].default_value[1]
                diffuseColorBlue = surfaceNode.inputs["Color"].default_value[2]
            if "Emission" in surfaceNode.inputs:
                # if surfaceNode.inputs["Emission"].is_linked:
                emissiveRed = surfaceNode.inputs['Emission'].default_value[0]
                emissiveGreen = surfaceNode.inputs['Emission'].default_value[1]
                emissiveBlue = surfaceNode.inputs['Emission'].default_value[2]
                emissiveAlpha = surfaceNode.inputs['Emission'].default_value[3]
                if not (0, 0, 0, 1) == (emissiveRed,emissiveGreen,emissiveBlue,emissiveAlpha):  #exclude default
                    m_data["emissiveColor"]  = "{:g} {:g} {:g} {:g}".format(emissiveRed,emissiveGreen,emissiveBlue,emissiveAlpha)

            if "Roughness" in surfaceNode.inputs:
                # if surfaceNode.inputs["Roughness"].is_linked:
                smoothness = 1 - surfaceNode.inputs['Roughness'].default_value
            if "Metallic" in surfaceNode.inputs:
                # if surfaceNode.inputs["Metallic"].is_linked:
                metallic = surfaceNode.inputs['Metallic'].default_value
            if "Specular" in surfaceNode.inputs:
                # if surfaceNode.inputs["Specular"].is_linked:
                specularIntensity = surfaceNode.inputs['Specular'].default_value

        # Check if "Reflectionmap" needs to be inserted in i3d
        if "customShader" in m_mat.keys() and "mirrorShader.xml" in m_mat["customShader"]:
            m_data["needsReflectionMap"] = True

        # kb actually using a material param for relfection 
        # note I know I can use get attribute or something clever I just want it step by step debuggable
        if "customParameter_useReflection" in m_mat:
            if m_mat["customParameter_useReflection"] == True:
                m_data["needsReflectionMap"] = True

        # setup refraction data 
        if "customParameter_useRefraction" in m_mat:
            if m_mat["customParameter_useRefraction"] == True :
                m_data["needsRefraction"] = True
                m_data["refractionCoeff"] = "{:g}".format(m_mat.get("customParameter_refractionCoeff", 1.0))
                m_data["refractionBumpScale"] = "{:g}".format(m_mat.get("customParameter_refractionBumpScale", 0.1))

        m_data["diffuseColor"]  = "{:g} {:g} {:g} 1".format(diffuseColorRed,diffuseColorGreen,diffuseColorBlue)
        if (0, 0, 0) == (diffuseColorRed,diffuseColorGreen,diffuseColorBlue):
            del m_data["diffuseColor"]

        m_data["specularColor"]  = "{:g} {:g} {:g}".format(smoothness,specularIntensity,metallic)

        if(m_mat.blend_method == 'BLEND'):
            m_data["alphaBlending"] = "true"

        if m_mat.use_backface_culling == False : 
        	m_data["doubleSided"] = "true"

        if 'shadingRate' in m_mat.keys():
            m_data['shadingRate'] = m_mat['shadingRate']

        if 'materialSlotName' in m_mat.keys():
            m_data['materialSlotName'] = m_mat['materialSlotName']
        if ("customShaderVariation") in m_mat.keys():
            m_data["customShaderVariation"] = m_mat["customShaderVariation"]
        m_files = getMaterialFiles(m_nodeStr)
        m_customParameters = {}
        m_customTextures = {}
        m_customBuffers = {}
        for m_file, m_type in m_files.items():
            if ("Texture"      == m_type): m_data["Texture"]      = m_file
            if ("Glossmap"     == m_type): m_data["Glossmap"]     = m_file
            if ("Normalmap"    == m_type):
                m_data["Normalmap"]    = m_file
                normalMapStrength = getNormalMapStrength(m_mat)
                if(normalMapStrength != 1):
                    m_data["bumpDepth"] = normalMapStrength
            if ("Emissivemap"   == m_type): m_data["Emissivemap"]   = m_file
            if ("customShader" == m_type): m_data["customShader"] = m_file
            if (0 == m_file.find("customTexture_")):                
                m_key = m_file.split("customTexture_")[1]
                m_customTextures[m_key] = m_type
            if (0 == m_file.find("customBuffer_")):                
                m_key = m_file.split("customBuffer_")[1]
                m_customBuffers[m_key] = m_type

        handledParams = []
        
        
        
 #       for m_item in m_mat.keys():
 #           if (0 == m_item.find("customParameter_")):
 #               m_key = m_item.split("customParameter_")[1]
 #               m_customParameters[m_key] = m_mat[m_item]
 #               handledParams.append(m_key)

        # Add params selected through a parameter template and not overriden by a user-defined value.
        shaderFileData = None
        if "customShader" in m_mat:
            #take shader location to put together an absolute path
            shaderFile = m_mat["customShader"]
            shaderFilePath = os.path.normpath(os.path.join(bpy.path.abspath("//"), shaderFile))
            if shaderFile.startswith("$"):
                shaderFilePath = shaderFile
            shaderFileData = i3d_shaderUtil.extractXMLShaderData(shaderFilePath)
        if shaderFileData is not None and "parameterTemplates" in shaderFileData:
            shaderParamMappings = None
            if "customMappings" in m_mat:
                 #take shader location to put together an absolute path
                mappingsFile = m_mat["customMappings"]
                mappingsFilePath = os.path.normpath(os.path.join(bpy.path.abspath("//"), mappingsFile))
                if mappingsFile.startswith("$"):
                    mappingsFilePath = mappingsFile
                shaderParamMappings = i3d_shaderUtil.extractXMLParamaterMappingData(mappingsFilePath)
 
            ## additional work for custom params. 
            # first get the variation information 
            customShaderVariation = None
            if "customShaderVariation" in m_mat:
                customShaderVariation = m_mat["customShaderVariation"]
                if customShaderVariation == "None":
                    customShaderVariation = None

            includeGroups = ["base"]
            if customShaderVariation != None:
                variation_groups_str = shaderFileData["variations_groups"][customShaderVariation]
                if variation_groups_str is not None:
                    includeGroups = variation_groups_str.split()

            pollshaderforparams = shaderParamMappings != None and "customParameter_takeParamFromShaderNodeName" in m_mat and m_mat["customParameter_takeParamFromShaderNodeName"] == "True"
            # walk through the params and skip the ones not used 
            for name, defaultvalue in shaderFileData["parameters"].items():
                parameter_group = shaderFileData["parameters_group"][name]
                if parameter_group is None or parameter_group not in includeGroups: 
                    continue

                matParam = "customParameter_" + name
                if matParam in m_mat :
                    m_customParameters[name] = m_mat[matParam]
                    handledParams.append(name)
                elif pollshaderforparams and name in shaderParamMappings["paramatersblenderMaterialLinkDict"]:
                    _numberElements = 0
                    # this is a little numpty but it works 
                    paramType = shaderFileData["parameterTypes"][name]
                    if paramType == 'float4':
                        _numberElements = 4
                    elif paramType == 'float3':
                            _numberElements = 3
                    elif paramType == 'float2':
                        _numberElements = 2
                    elif paramType == 'float':
                        _numberElements = 1
                    if _numberElements > 0 :
                        shadervalue = i3d_shaderUtil.getMaterialShaderFloatParam(m_nodeStr, shaderParamMappings["paramatersblenderMaterialLinkDict"][name], _numberElements)
                        if shadervalue :
                            stringValue = ""
                            if isinstance(shadervalue, float) :
                                stringValue = "{:.3f}".format(shadervalue)
                            else :
                                stringValue = " ".join(f"{part:.3f}" for part in shadervalue)
                            m_customParameters[name] = stringValue
                            handledParams.append(name)

            for parameterTemplateId, parameterTemplate in shaderFileData["parameterTemplates"].items():
                selectedParentSubTemplateId = None
                subTemplateId = parameterTemplate["rootSubTemplateId"]
                while subTemplateId is not None:
                    subTemplate = parameterTemplate["subtemplates"][subTemplateId]
                    parentSubTemplateId = subTemplate["parentId"]

                    subTemplateKey = "customParameterTemplate_{}_{}".format(parameterTemplateId, subTemplateId)
                    selectedSubTemplateId = None
                    if subTemplateKey in m_mat:
                        selectedSubTemplateId = m_mat[subTemplateKey]
                    elif selectedParentSubTemplateId is not None:
                        selectedSubTemplateId = selectedParentSubTemplateId

                    if selectedSubTemplateId is not None:
                        selectedSubTemplate = subTemplate["templates"][selectedSubTemplateId]
                        for paramName, _ in parameterTemplate["parameters"].items():
                            if paramName not in handledParams and paramName in selectedSubTemplate:
                                m_customParameters[paramName] = selectedSubTemplate[paramName]
                                handledParams.append(paramName)

                        if "parentTemplate" in selectedSubTemplateId:
                            selectedParentSubTemplateId = selectedSubTemplateId["parentTemplate"]
                        else:
                            selectedParentSubTemplateId = subTemplate["defaultParentTemplate"]

                    subTemplateId = parentSubTemplateId

        if len(m_customParameters):
            m_data["CustomParameter"] = m_customParameters
        if len(m_customTextures):
            m_data["Custommap"] = m_customTextures
        if len(m_customBuffers):
            m_data["CustomBuffer"] = m_customBuffers
    return m_data

def getLightData(m_nodeStr, m_light):
    """ Configure  export parameters according to the light properties """

    if (isObjDataExists(m_nodeStr,"type")):
        m_type = getObjData(m_nodeStr,"type")
        #case 'AREA' not supported by GIANTSEditor
        if ('SUN'   == m_type): m_light["type"] = "directional"
        if ('POINT' == m_type): m_light["type"] = "point"
        if ('SPOT'  == m_type):
            m_light["type"] = "spot"
            if (isLightDataExists(m_nodeStr,"spot_size")):
                m_light["coneAngle"] = "{:g}".format(math.degrees(getLightDataFromAPI(m_nodeStr,"spot_size")))
            if (isLightDataExists(m_nodeStr,"spot_blend")):
                m_light["dropOff"] = "{:.3f}".format(5.0*getLightDataFromAPI(m_nodeStr,"spot_blend"))
    if (isLightDataExists(m_nodeStr,"color")):
        m_color = getLightDataFromAPI(m_nodeStr,"color")
        m_light["color"] = "{:g} {:g} {:g}".format(m_color.r,m_color.g,m_color.b)
    if (isLightDataExists(m_nodeStr,"cutoff_distance")):
        m_light["range"] = "{:.2f}".format(getLightDataFromAPI(m_nodeStr,"cutoff_distance"))
    if (isLightDataExists(m_nodeStr,"use_shadow")):
        m_castShadowMap = getLightDataFromAPI(m_nodeStr,"use_shadow")
        if (m_castShadowMap):  m_light["castShadowMap"] = "true"
        else: m_light["castShadowMap"] = "false"
    return m_light

def getCameraData(m_nodeStr, m_camera):
    """ Configure  export parameters according to the camera properties """

    if (isObjDataExists(m_nodeStr,"lens")):
        m_camera["fov"] = "{:.3f}".format(getObjData(m_nodeStr,"lens"))
    if (isObjDataExists(m_nodeStr,"clip_start")):
        m_camera["nearClip"] = "{:g}".format(getObjData(m_nodeStr,"clip_start"))
    if (isObjDataExists(m_nodeStr,"clip_end")):
        m_camera["farClip"] = "{:g}".format(getObjData(m_nodeStr,"clip_end"))
    if (isObjDataExists(m_nodeStr,"type")):
        m_type = getObjData(m_nodeStr,"type")
        if ('ORTHO'== m_type):
            m_camera["orthographic"] = "true"
            if (isObjDataExists(m_nodeStr,"ortho_scale")):
                m_camera["orthographicHeight"]  = "{}".format(getObjData(m_nodeStr,"ortho_scale"))
    return m_camera

def isLightDataExists(m_nodeStr,m_parm):
    m_str = 'bpy.data.objects["{}"].data.{}'.format(m_nodeStr,m_parm)
    try:
        eval(m_str)
        return True
    except:
        return False

def getLightDataFromAPI(m_nodeStr,m_parm):
    m_str = 'bpy.data.objects["{}"].data.{}'.format(m_nodeStr,m_parm)
    return eval(m_str)

def setLightData(m_nodeStr, m_parm, m_value):
    if hasattr(bpy.data.objects[m_nodeStr].data, m_parm):
        setattr(bpy.data.objects[m_nodeStr].data, m_parm, m_value)

def isObjDataExists(m_nodeStr,m_parm):
    m_str = 'bpy.data.objects["{}"].data.{}'.format(m_nodeStr,m_parm)
    try:
        eval(m_str)
        return True
    except:
        return False

def getObjData(m_nodeStr,m_parm):
    m_str = 'bpy.data.objects["{}"].data.{}'.format(m_nodeStr,m_parm)
    return eval(m_str)

def addChildObjects(m_nodes,m_result):
    """
    Appends all names of m_nodes and all their children to m_result.

    :param m_nodes: list of nodes without a parent
    :param m_result: list of all nodes which are a children of another node.
    """
    for m_nodeStr in m_nodes:
        m_result.append(m_nodeStr)
        m_childs = getChildObjects(m_nodeStr)
        addChildObjects(m_childs,m_result)

def boneHasParentBone(boneStr, armatureStr):
    """
    Returns True if the bone has a parent node.
    """
    bone = bpy.data.objects[armatureStr].data.bones[boneStr]
    if(bone.parent):
        return True
    return False

def boneHasChildBone(boneStr, armatureStr):
    """ Returns True if the bone has a child node. """

    bone = bpy.data.objects[armatureStr].data.bones[boneStr]
    if(bone.children):
        return True
    return False

def getBoneParent(boneStr, armatureStr):
    """ Returns the name of the parent if it has a parent. """

    if(boneHasParentBone(boneStr,armatureStr)):
        return bpy.data.objects[armatureStr].pose.bones[boneStr].parent.name
    return ""

def getBoneNameList(armatureStr):
    """ Returns a list of all bone names of the object if it has bones """

    if(bpy.data.objects[armatureStr].data.bones):    #hasBones, alternative check if type armature
        return  bpy.data.objects[armatureStr].data.bones.keys()
    return []

def isType(m_objStr, m_type):
    try:
        if m_objStr in bpy.data.objects :
            return (bpy.data.objects[m_objStr].type == m_type)
    except:
        pass
    return False

def isTypeArmature(objStr):
    return isType(objStr,"ARMATURE")

def isTypeMesh(objStr):
    return isType(objStr,"MESH")

def getAppliedArmatureName(objStr):
    """
    multiple armature modifiers not supported

    :returns: the armature name which is applied on given object
    """
    try:
        obj = bpy.data.objects[objStr]
        for modifier in obj.modifiers:
            if modifier.type == "ARMATURE":
                return modifier.object.name
    except:
        pass
    return None

def getSingleBoneInfluence(objStr):
    """
    Decides if only a single bone has influene on a vertex

    Returns the single Vertex Group which influences a mesh if it exists.
    Therefore every vertex must be assigned to exactly one group with weight 1.0
    """
    try:
        verticesVertexGroups = []
        for vertice in bpy.data.objects[objStr].data.vertices:  #all vertices
            if len(vertice.groups) >= 1:
                for vertexGroup in vertice.groups:                  #all assigned groups
                    # print("objStr: {}\tindex: {}, weight: {}".format(objStr,vertexGroup.group,vertexGroup.weight))
                    if vertexGroup.weight == 1.0:                   #must have weight 1
                        verticesVertexGroups.append(vertexGroup.group)
                    elif vertexGroup.weight == 0.0:                 #can have 0 weight groups
                        pass
                    else:
                        return None
        verticesVertexGroups = list(set(verticesVertexGroups))
        if len(verticesVertexGroups) == 1:
            for vertexGroup in bpy.data.objects[objStr].vertex_groups:
                if vertexGroup.index == verticesVertexGroups[0]:
                    return vertexGroup.name
    except:
        pass
    return None

def hasBone(m_objStr):
    """ Return True if object is armature and has bones assigned. """

    try:
        if bpy.data.objects[m_objStr].data.bones:
            return True
    except:
        #no armature
        pass
    return False

def hasAnimation(m_objStr):
    """ Returns True if the given object has animations """

    try:
        obj = bpy.data.objects[m_objStr]
        for action in bpy.data.actions:
            for track in obj.animation_data.nla_tracks:
                for strip in track.strips:
                    if( action is strip.action):
                        return True
    except:
        pass
    try:
        obj = bpy.data.objects[m_objStr]
        for action in bpy.data.actions:
            if (action is obj.animation_data.action):
                return True
    except:
        pass
    return False

def hasObject(objStr):
    """ Returns True if the given object exists in bpy.data.objects """

    return objStr in bpy.data.objects

def isBoneOfArmature(m_boneStr,m_armStr):
    """ Returns True if the given bone is part of the armature """

    return m_boneStr in bpy.data.objects[m_armStr].pose.bones

def action_type(action):
    """Determines the type of animations contained within the action."""
    has_shape_keys = False
    has_skinning = False
    has_visibility = False
    has_other = False

    if not action:
        return "none"

    for fcurve in action.fcurves:
        if fcurve.data_path.startswith('key_blocks'):
            has_shape_keys = True
        elif fcurve.data_path.startswith(('pose.bones', 'location', 'rotation', 'scale')):
            has_skinning = True
        elif fcurve.data_path in {'hide', 'hide_render', 'hide_viewport'}:
            has_visibility = True
        else:
            has_other = True

    categories = []
    if has_shape_keys:
        categories.append("shape_keys")
    if has_skinning:
        categories.append("skinning")
    if has_visibility:
        categories.append("visibility")
    if has_other:
        categories.append("other")

    if len(categories) > 1:
        return "mix: " + ", ".join(categories)
    elif categories:
        return categories[0]
    else:
        return "none"


def getActionsByType(objStr, action_type_filter):
    """Returns a list of action names assigned to the provided object that match the specified action type."""
    action_names = []

    obj = bpy.data.objects[objStr]
    if not obj.animation_data:
        return action_names

    # Check NLA tracks
    for track in obj.animation_data.nla_tracks:
        for strip in track.strips:
            action_type_result = action_type(strip.action)
            if strip.action and action_type_result == action_type_filter:
                action_names.append(strip.action.name)

    # Check the currently active action
    if obj.animation_data.action:
        action_type_result = action_type(obj.animation_data.action)
        if action_type_result == action_type_filter:
            action_names.append(obj.animation_data.action.name)

    # Remove duplicates
    action_names = list(set(action_names))
    return action_names

def getFcurveDataOfAction(action, boneStr):
    """ Returns raw data gathered from the fcurves, no modifier applied. """

    fcurves = {}
    arrayIndexToParameterQuaternion = { 0: "w", 1: "x", 2: "y", 3: "z"}
    arrayIndexToParameterXYZ = {0:"x",1:"y",2:"z"}
    interpolationTransform = {'LINEAR': "linear",'BEZIER':'linear','CONSTANT':'constant'}
    for fcrv in bpy.data.actions[action].fcurves:   #get action from clip parent
        keyframePoints = {}
        boneName = boneStr.split("_")[-1]           #to be save
        if(fcrv.group.name == boneName):
            if("quaternion" in fcrv.data_path.split(".")[-1]):
                dataPath = fcrv.data_path.split(".")[-1] + "_" + arrayIndexToParameterQuaternion[fcrv.array_index]
            else:
                dataPath = fcrv.data_path.split(".")[-1] + "_" + arrayIndexToParameterXYZ[fcrv.array_index]
            for kfp in fcrv.keyframe_points:
                data = {}
                timestamp = kfp.co.x
                data['value'] = kfp.co.y
                data['interpolation'] = interpolationTransform[kfp.interpolation]
                keyframePoints[timestamp] = data
            fcurves[dataPath] = keyframePoints
    return fcurves

def __getFcurveData(fcurve):    #unused

    interpolationTransform = {'LINEAR': "linear",'BEZIER':'bezier','CONSTANT':'constant'}
    fcurveData = {}
    for key, item in fcurve.items(): #fcurves
        for keyframePoint in item.keyframe_points:
            fcurveData['timestamp'] = keyframePoint.co.x
            fcurveData['value'] = keyframePoint.co.y
            fcurveData['interpolation'] = interpolationTransform[keyframePoint.interpolation]

def getActionOwners(actionStr):
    """ Returns owner of the requested action by name """

    ownersList = []
    for obj in bpy.data.objects:
        if(hasAnimation(obj.name)):
            actionNames = getActionsByType(obj.name, "skinning" )
            if (actionStr in actionNames):
                ownersList.append(obj.name)
    return ownersList

def getActionGroupNames(action):
    """ Returns a list of all groups used in the requested action. if it has more than one group, it must be bones """

    groupNames = []
    for group in bpy.data.actions[action].groups:
        groupNames.append(group.name)
    return groupNames

def calculateClipDuration(actStr):
    """ Returns the length of the action in ms. """

    m_fps = bpy.context.scene.render.fps
    return (bpy.data.actions[actStr].frame_range[1] - bpy.data.actions[actStr].frame_range[0]) * m_fps

def getFps():
    return bpy.context.scene.render.fps

def toDegrees(radiant):
    return math.degrees(radiant)

def quaternionToEulerFormat(quaternion):    #w,x,y,z
    quat = mathutils.Quaternion((quaternion[0], quaternion[1], quaternion[2], quaternion[3]))
    euler = quat.to_euler()
    return [euler.x,euler.y,euler.z]

def getNodeIndex( m_nodeStr ):
    return getDepth(m_nodeStr,"")

def getIndex( m_nodeStr ):
    m_node = bpy.data.objects[m_nodeStr]
    m_objParent = m_node.parent
    # if parented to the world
    if (None == m_objParent):
        m_iterItems = getWorldObjects()
    else:
        m_iterItems = getChildObjects(m_objParent.name)
    for i in range(len(m_iterItems)):
        m_child = m_iterItems[i]
        if (m_node.name == m_child):
            return i
    return None

def getDepth( m_nodeStr, m_ind ):
    """ return the configuration index for the XML configuration file """

    if not m_nodeStr in bpy.data.objects:
        return ""
    m_node = bpy.data.objects[m_nodeStr]
    m_index = getIndex( m_node.name )
    m_objParent = m_node.parent
    # if parented to the world
    if (None == m_objParent):
        m_ind   = "{}>{}".format( m_index, m_ind ) # last run
        return m_ind
    else:
        if "" == m_ind:
            m_ind   = "{}{}".format( m_index, m_ind ) # first run
        else:
            m_ind   = "{}|{}".format( m_index, m_ind )
        m_ind = getDepth( m_objParent.name, m_ind )
    return m_ind

def getWorldObjects():
    """  Returns all bpy.data.objects without a parent. """

    m_iterItems = []

    for m_node in bpy.context.scene.objects:    #why context not bpy.data.objects
        if (None is m_node.parent):
            m_iterItems.append(m_node.name)
    m_iterItems.sort(key=natural_keys)
    return m_iterItems

def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]

def getNodeUserAttributes(m_nodeStr):
    m_attributes = []
    m_types = ["boolean","string","scriptCallback","float"]
    if m_nodeStr in bpy.data.objects:
        m_node = bpy.data.objects[m_nodeStr]
        for m_key in m_node.keys():
            if (0==m_key.find("userAttribute_")):
                try:
                    m_list = m_key.split("_",2)
                    m_type = m_list[1]
                    m_name = m_list[2]
                    m_val  = m_node[ m_key ]
                    if m_type in m_types:
                        if ("boolean"==m_type):
                            if m_val: m_val = "true"
                            else:     m_val = "false"
                        m_val = "{}".format(m_val)
                        m_item = {}
                        m_item["name"]  = m_name
                        m_item["type"]  = m_type
                        m_item["value"] = m_val
                        m_attributes.append(m_item)
                except:
                    pass
    return m_attributes


def getCurveLength(curveName):
    """ calculates the length of the given curve """

    if curveName in bpy.data.objects and bpy.data.objects[curveName].type == "CURVE":
        try:
            return bpy.data.objects[curveName].data.splines[0].calc_length(resolution = 1024)
        except Exception as e:
            print(e)
            pass
    return -1


def deleteHierarchy(obj):
    """ Recursively delete the provided object with all it's children. """

    def remove_child_objects(obj):       # recursion
        for child in obj.children:
            if child.children:
                remove_child_objects(child)

            bpy.data.objects.remove(child,do_unlink = True)
    remove_child_objects(obj)
    bpy.data.objects.remove(obj,do_unlink = True)

def getFcurveLength(action):
    """ Returns a dictionary with the distance as key and the frame as value, for the given action's fcurves """

    kfpCount = 1
    # print("action: {}, name: {}".format(action,action.name))
    for fcrvs in action.fcurves:
        # print("fcurvs has {} kfp".format(len(fcrvs.keyframe_points)))
        kfpCount = max(kfpCount,len(fcrvs.keyframe_points))
    # resolution = kfpCount * 100
    resolution = kfpCount * 100

    frameRange = action.frame_range
    frameStep = (frameRange[1] - frameRange[0])/(resolution -1)
    xyzFcurves = [fcvs for fcvs in action.fcurves if 'location' in fcvs.data_path]  #x y z
    distance = 0
    distToFrame = []
    previousFrame = 0
    for i in range(resolution):
        frame = frameRange[0] + (frameStep)*i
        localDistance = 0
        for fc in xyzFcurves:  #euclidian distance (x2-x1^2 + y2-y1^2 + z2-z1^2)^0.5
            localDistance += (fc.evaluate(previousFrame)-fc.evaluate(frame))**2
        distance += localDistance**0.5
        distToFrame.append((distance,frame))
        previousFrame = frame
    #distance is distToFram[-1]
    return distToFrame


def createBezierCurveFromAnimation(objName):
    """ Creates a bezier curve form the animation data and returns the Curve object. """

    tempCurve = bpy.data.curves.new('tempCurve_{}'.format(objName), 'CURVE')
    tempCurve.dimensions = '3D'
    animFcurves = bpy.data.objects[objName].animation_data.action.fcurves
    # index 1 is the Y location fcurve
    srcFcurve = animFcurves.find('location', index=1)
    spline = tempCurve.splines.new('BEZIER')
    spline.bezier_points.add(count=len(srcFcurve.keyframe_points)-1)
    fcurves = zip(*(animFcurves.find('location', index=k).keyframe_points[:] for k in range(3)))
    t = 0
    for xp, yp, zp in fcurves:
        p = spline.bezier_points[t]
        p.co = (xp.co.y, yp.co.y, zp.co.y)
        p.handle_left = (xp.handle_left.y, yp.handle_left.y, zp.handle_left.y)
        #ht = 'AUTO' if xp.handle_left == 'AUTO_CLAMPED' else xp.handle_left_type
        p.handle_left_type = 'FREE'
        p.handle_right = (xp.handle_right.y, yp.handle_right.y, zp.handle_right.y)
        #ht = 'AUTO' if xp.handle_right == 'AUTO_CLAMPED' else xp.handle_right_type
        p.handle_right_type = 'FREE'
        t += 1

    obj = bpy.data.objects.new('tempObj_{}'.format(objName), tempCurve)
    bpy.context.scene.collection.objects.link(obj)

    return obj
#------------------------------------------------------------------------
#------------------------------------------------------------------------
#------------------------------------------------------------------------
class IndexBufferItem(object):
    def __init__(self, m_vertItem, m_mat):
        # Extract relevant parts from m_vertItem, handling missing or empty extradata
        data = m_vertItem.get("data", {})
        extradata = m_vertItem.get("extraData", {})
        
        # Create a tuple of relevant items
        items = (m_mat, tuple(data.items()), tuple(extradata.items()))
        
        # Create a hash of the tuple
        self._hash = hash(items)

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return self._hash == other._hash



###################################################################################
###### custom shape attributes ############################
###################################################################################

g_Global_I3D_CustomShapeAttributes = {}


class DataFormat:
    formats = {
        'float': {'length': 1, 'type': float},
        'float2': {'length': 2, 'type': float},
        'float3': {'length': 3, 'type': float},
        'float3_force32bit': {'length': 3, 'type': float},
        'float4': {'length': 4, 'type': float},
        'int': {'length': 1, 'type': int},
        'int2': {'length': 2, 'type': int},
        'int3': {'length': 3, 'type': int},
        'int4': {'length': 4, 'type': int},
        'short2': {'length': 2, 'type': float},
        'short4': {'length': 4, 'type': float},
        'short2n': {'length': 2, 'type': float},
        'short4n': {'length': 4, 'type': float},
        '32bitqt': {'length': 4, 'type': float},
        'ubyte4': {'length': 4, 'type': int},
        'ubyte4n': {'length': 4, 'type': float},
        'uint': {'length': 1, 'type': int},
        'colourubyte4': {'length': 4, 'type': float},
    }

    @staticmethod
    def format_data(data, data_format):
        if data_format not in DataFormat.formats:
            raise ValueError(f"Unsupported data format: {data_format}")

        format_info = DataFormat.formats[data_format]
        expected_length = format_info['length']
        data_type = format_info['type']

        # Fill data with zeros if it is shorter than expected
        if len(data) < expected_length:
            data = list(data) + [0] * (expected_length - len(data))

        # Convert data to the correct type
        formatted_data = [data_type(d) for d in data[:expected_length]]

        # Create a format string based on the type
        if data_type == int:
            format_string = ' '.join(['{:d}'] * expected_length)
        elif data_type == float:
            format_string = ' '.join(['{:g}'] * expected_length)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

        # Apply the format string to the formatted data
        return format_string.format(*formatted_data)

class VertexAttribute:
    def __init__(self, shader_attrib_type, shape_file_attrib_name, data_format, blender_vertex_mapping):
        self.shader_attrib_type = shader_attrib_type
        self.shape_file_attrib_name = shape_file_attrib_name
        self.data_format = data_format
        self.blender_vertex_mapping = blender_vertex_mapping
        self.mappings = self.parse_mappings(blender_vertex_mapping)

    def parse_mappings(self, blender_vertex_mapping):
        mappings = []
        segments = blender_vertex_mapping.split(';')
        for segment in segments:
            segment = segment.strip()
            if segment:
                mappings.append(self.parse_mapping(segment))
        return mappings

    @staticmethod
    def parse_mapping(mapping):
        function_match = re.match(r'function\(([^()]+)\)', mapping)
        if function_match:
            return VertexAttribute.parse_function(mapping)
        
        if 'Shape Key' in mapping:
            parts = mapping.split('->')
            if len(parts) == 3:
                shape_key_name = parts[1]
                attribute_components = parts[2].split('[')
                attribute = attribute_components[0]
                component_indices = VertexAttribute.parse_component_indices(attribute_components[1][:-1]) if len(attribute_components) > 1 else []
                return ('shape_key', shape_key_name, attribute, component_indices)
            else:
                raise ValueError(f"Invalid shape key mapping format: {mapping}")
        else:
            attribute_components = mapping.split('[')
            if len(attribute_components) == 2:
                attribute = attribute_components[0]
                component_indices = VertexAttribute.parse_component_indices(attribute_components[1][:-1])
            else:
                attribute = mapping.strip()  # If no indices are provided
                component_indices = []
            return ('mesh', attribute, component_indices)

    @staticmethod
    def parse_function(mapping):
        # This regex matches the function pattern and splits it into name, data buffer, and arguments
        function_regex = re.compile(r'function\(([^)]+)\)')
        match = function_regex.match(mapping)
        if not match:
            raise ValueError(f"Invalid function mapping format: {mapping}")

        params_str = match.group(1)
        params = VertexAttribute.split_params(params_str)
        func_name = params[0].strip()
        data_buffer = params[1].strip()
        args = [param.strip().strip('"') for param in params[2:]]

        if data_buffer.startswith('function('):
            data_buffer = VertexAttribute.parse_function(data_buffer)
        else:
            attribute_components = data_buffer.split('[')
            if len(attribute_components) == 2:
                attribute = attribute_components[0].strip()
                component_indices = VertexAttribute.parse_component_indices(attribute_components[1][:-1])
            else:
                attribute = data_buffer.strip()  # If no indices are provided
                component_indices = []

            data_buffer = ('data', attribute, component_indices)

        return ('function', func_name, data_buffer, args)

    @staticmethod
    def split_params(params_str):
        params = []
        start = 0
        nested_level = 0
        for i, char in enumerate(params_str):
            if char == ',' and nested_level == 0:
                params.append(params_str[start:i].strip())
                start = i + 1
            elif char == '(':
                nested_level += 1
            elif char == ')':
                nested_level -= 1
        params.append(params_str[start:].strip())
        return params

    @staticmethod
    def parse_component_indices(components):
        if ':' in components:
            start, end = components.split(':')
            start = int(start) if start else None
            end = int(end) if end else None
            return list(range(start, end)) if start is not None else list(range(end))
        elif components:
            return [int(components)]
        else:
            return []
    
    @staticmethod
    def from_xml_element(element):
        try:
            shader_attrib_type = element.get('shaderattributetype')
            shape_file_attrib_name = element.get('shapefileattributename')
            data_format = element.get('dataformat')
            blender_vertex_mapping = element.get('blendervertexmapping')
            if not (shader_attrib_type and shape_file_attrib_name and data_format and blender_vertex_mapping):
                print("Error: Missing required attribute in XML element.")
                return None
            return VertexAttribute(shader_attrib_type, shape_file_attrib_name, data_format, blender_vertex_mapping)
        except Exception as e:
            print(f"Error parsing XML element: {e}")
            return None

    # static list
    cached_keyshapemeshes = {}

    @staticmethod
    def clear_cache():
        for mesh in VertexAttribute.cached_keyshapemeshes.values():
            bpy.data.meshes.remove(mesh)

        VertexAttribute.cached_keyshapemeshes = {}

    @staticmethod
    def create_deformed_mesh_from_shape_key(mesh, shape_key_namefrom, shape_key_nameto, interpolateValue):
        if shape_key_nameto is None:
            interpolateValue = 0.0

        if interpolateValue == 0.0:
            shape_key_nameto = None

        if interpolateValue == 1.0:
            shape_key_namefrom = shape_key_nameto
            shape_key_nameto = None

        new_mesh_name = mesh.name + "_" + shape_key_namefrom

        if not mesh.shape_keys or shape_key_namefrom not in mesh.shape_keys.key_blocks:
            print(f"Error: Shape key '{shape_key_namefrom}' not found in mesh '{mesh.name}'")
            return None

        if shape_key_nameto is not None and shape_key_nameto not in mesh.shape_keys.key_blocks:
            print(f"Error: Shape key '{shape_key_nameto}' not found in mesh '{mesh.name}'")
            return None

        if shape_key_nameto is not None:
            new_mesh_name += "_" + shape_key_nameto + "_" + str(interpolateValue)

        if new_mesh_name in VertexAttribute.cached_keyshapemeshes:
            return VertexAttribute.cached_keyshapemeshes[new_mesh_name]

        # Create a new mesh data block
        new_mesh = mesh.copy()
        new_mesh.name = new_mesh_name

        # Apply the shape key deformation
        shape_key_from = mesh.shape_keys.key_blocks[shape_key_namefrom]
        if shape_key_nameto is not None:
            shape_key_to = mesh.shape_keys.key_blocks[shape_key_nameto]
            for i, vertex in enumerate(new_mesh.vertices):
                vertex.co = shape_key_from.data[i].co.lerp(shape_key_to.data[i].co, interpolateValue)
        else:
            for i, vertex in enumerate(new_mesh.vertices):
                vertex.co = shape_key_from.data[i].co

        # Recalculate normals to reflect the new geometry
        new_mesh.update()
        new_mesh.calc_normals_split()

        new_mesh.update()

        VertexAttribute.cached_keyshapemeshes[new_mesh_name] = new_mesh
        return new_mesh

            
    def buildvertexattribute(self, vertItem, m_meshGen, m_loop, vertex, matrixTransform, bakeTransforms, showWarning, frame=None):
        mesh = m_meshGen
        loop = m_loop
        vertex = vertex
        data = []

        for mapping in self.mappings:
            data.extend(self.handle_mapping(mapping, mesh, loop, vertex, matrixTransform, bakeTransforms, showWarning, frame))

        vertItem[self.shape_file_attrib_name] = DataFormat.format_data(data, self.data_format)

    def handle_mapping(self, mapping, mesh, loop, vertex, matrixTransform, bakeTransforms, showWarning, frame):
        if mapping[0] == 'function':
            return self.execute_function(mapping, mesh, loop, vertex, matrixTransform, bakeTransforms, showWarning)
        elif mapping[0] == 'shape_key':
            shapemesh = VertexAttribute.create_deformed_mesh_from_shape_key(mesh, mapping[1], None, 0.0)
            if shapemesh == None:
                raise Exception("Can not find shape meshg for %s" % mapping[1] )
            shape_vertex = shapemesh.vertices[vertex.index]
            shape_loop = shapemesh.loops[loop.index]
            return self.get_mesh_data(shapemesh, shape_loop, shape_vertex, matrixTransform, bakeTransforms, mapping[2], mapping[3], showWarning)
        elif mapping[0] == 'mesh':
            if frame != None:
                shapemesh = VertexAttribute.create_deformed_mesh_from_shape_key(mesh, frame["from"] , frame["to"], frame["interpolate"] )
                shape_vertex = shapemesh.vertices[vertex.index]
                shape_loop = shapemesh.loops[loop.index]
                return self.get_mesh_data(shapemesh, shape_loop, shape_vertex, matrixTransform, bakeTransforms, mapping[1], mapping[2],showWarning)
            else:
                return self.get_mesh_data(mesh, loop, vertex, matrixTransform, bakeTransforms, mapping[1], mapping[2], showWarning)
        else:
            return []

    def execute_function(self, function_mapping, mesh, loop, vertex, matrixTransform, bakeTransforms, showWarning):
        func_name = function_mapping[1]
        func = getattr(self, func_name, None)
        if func:
            nested_data = []
            if function_mapping[2][0] == 'function':
                nested_data = self.execute_function(function_mapping[2], mesh, loop, vertex, matrixTransform, bakeTransforms, showWarning)
            elif function_mapping[2][0] == 'shape_key':
                parts = function_mapping[2][1].split('->')
                shape_key_name = parts[1]
                attribute_components = parts[2].split('[')
                attribute = attribute_components[0]
                component_indices = VertexAttribute.parse_component_indices(attribute_components[1][:-1]) if len(attribute_components) > 1 else []
                shapemesh = VertexAttribute.create_deformed_mesh_from_shape_key(mesh, shape_key_name, None, 0.0)
                shape_vertex = shapemesh.vertices[vertex.index]
                shape_loop = shapemesh.loops[loop.index]
                nested_data = self.get_mesh_data(shapemesh, shape_loop, shape_vertex, matrixTransform, bakeTransforms, attribute, component_indices, showWarning)
            else:
                nested_data = self.get_mesh_data(mesh, loop, vertex, matrixTransform, bakeTransforms, function_mapping[2][1], function_mapping[2][2], showWarning)
            return func(mesh, loop, vertex, matrixTransform, bakeTransforms, function_mapping[2][1], function_mapping[2][2], showWarning, nested_data, *function_mapping[3])
        return []


    tangent_data_store = {}
    tangent_mesh_store = {}

    @staticmethod
    def generateTangentLayer(mesh, tangentUVlayer=None):
        # Use a unique key for the mesh and the UV layer
        mesh_id = id(mesh)

        # Determine the UV layer to use
        if tangentUVlayer and tangentUVlayer in mesh.uv_layers:
            uv_layer_name = tangentUVlayer
        elif mesh.uv_layers:
            # Default to the first UV layer if none specified
            uv_layer_name = mesh.uv_layers[0].name
        else:
            # If there are no UV layers, generate a default tangent pointing up
            uv_layer_name = None

        # Create unique keys for tangents and bitangents
        tangent_key = f"tangent_{uv_layer_name or 'default'}"
        bitangent_key = f"bitangent_{uv_layer_name or 'default'}"

        # Initialize the storage for this mesh and UV layer if not already present
        if mesh_id not in VertexAttribute.tangent_data_store:
            VertexAttribute.tangent_data_store[mesh_id] = {}
            VertexAttribute.tangent_mesh_store[mesh_id] = []

        # Early out if the tangent data already exists for this UV layer
        if tangent_key in VertexAttribute.tangent_data_store[mesh_id] and VertexAttribute.tangent_data_store[mesh_id][tangent_key]:
            #print(f"Tangent data already exists for {uv_layer_name}. Returning early.")
            return VertexAttribute.tangent_data_store[mesh_id][tangent_key], VertexAttribute.tangent_data_store[mesh_id][bitangent_key]

        # Initialize storage for this UV layer
        VertexAttribute.tangent_data_store[mesh_id][tangent_key] = {}
        VertexAttribute.tangent_data_store[mesh_id][bitangent_key] = {}

         # Copy the mesh to avoid modifying the original
        mesh_copy = mesh.copy()
        mesh_copy.update()
        mesh_copy.calc_normals_split()
        mesh_copy.update()

        VertexAttribute.tangent_mesh_store[mesh_id].append(mesh_copy)

        # Calculate tangents
        if uv_layer_name:
            # Set the active UV map and calculate tangents using Blender's built-in function
            mesh_copy.uv_layers.active = mesh_copy.uv_layers[uv_layer_name]
            mesh_copy.calc_tangents(uvmap=uv_layer_name)
            mesh_copy.update()
            # Store the tangent and bitangent data in the external dictionary
            for loop in mesh_copy.loops:
                VertexAttribute.tangent_data_store[mesh_id][tangent_key][loop.index] = loop.tangent
                VertexAttribute.tangent_data_store[mesh_id][bitangent_key][loop.index] = loop.bitangent_sign
        else:
            # If no UV layers, create a default tangent pointing up
            default_tangent = (0.0, 0.0, 1.0)
            for loop in mesh_copy.loops:
                VertexAttribute.tangent_data_store[mesh_id][tangent_key][loop.index] = default_tangent
                VertexAttribute.tangent_data_store[mesh_id][bitangent_key][loop.index] = 1.0

        #print(f"Tangent data has been generated and stored externally for the mesh with UV layer {uv_layer_name}.")
        return VertexAttribute.tangent_data_store[mesh_id][tangent_key], VertexAttribute.tangent_data_store[mesh_id][bitangent_key]


    @staticmethod
    def cleanupTangentLayers(mesh):
        # Use a unique key for the mesh and the UV layer
        mesh_id = id(mesh)

        # Check if there is any stored data for this mesh
        if mesh_id in VertexAttribute.tangent_data_store:
            # Clear all stored tangent and bitangent data for this mesh
            VertexAttribute.tangent_data_store.pop(mesh_id, None)

        if mesh_id in VertexAttribute.tangent_mesh_store:
            for mesh in VertexAttribute.tangent_mesh_store[mesh_id]:
                bpy.data.meshes.remove(mesh)
             
            VertexAttribute.tangent_mesh_store[mesh_id].clear()



    def get_mesh_data(self, mesh, loop, vertex, matrix_transform, bake_transforms, attributeInfo, component_indices, showWarning):
        data = None
        parts = attributeInfo.split(":", 1)  # Split at most once
        attribute = parts[0]
        otherinfo = parts[1] if len(parts) > 1 else None

        if attribute == 'position':
            if matrix_transform:
                pos_mat = mathutils.Matrix.Translation(vertex.co.xyz)
                pos_mat = matrix_transform @ pos_mat
                pos = pos_mat.to_translation()
            else:
                pos = vertex.co.xyz
            if bake_transforms:  # x z -y
                pos = (pos[0], pos[2], -pos[1])
            data = pos
        elif attribute == 'normal':
            if matrix_transform:
                normalMat = mathutils.Matrix.Translation(loop.normal)
                rotMat = matrix_transform.to_euler().to_matrix().to_4x4()
                normalMat = rotMat @ normalMat
                norm = normalMat.to_translation()[:]
            else:
                norm = loop.normal
            if bake_transforms:  # x z -y
                norm = (norm[0], norm[2], -norm[1])
            data = norm
        elif attribute == 'tangent':
            tangent_layer, bitangent_layer = VertexAttribute.generateTangentLayer(mesh, otherinfo)
            tangent = tangent_layer[loop.index]
            if matrix_transform:
                tangentMat = mathutils.Matrix.Translation(tangent)
                rotMat = matrix_transform.to_euler().to_matrix().to_4x4()
                tangentMat = rotMat @ tangentMat
                tangent = tangentMat.to_translation()[:]
            if bake_transforms:  # x z -y
                tangent = (tangent[0], tangent[2], -tangent[1])
            data = tangent
        elif attribute == 'bitangent_sign':
            # Assuming bitangent_sign is a scalar and doesn't need matrix transformation
            tangent_layer, bitangent_layer = VertexAttribute.generateTangentLayer(mesh, otherinfo)
           
            data = [bitangent_layer[loop.index]]
        elif attribute in mesh.uv_layers:
            uv_layer = mesh.uv_layers[attribute]
            data = uv_layer.data[loop.index].uv
        elif attribute in mesh.color_attributes:
            data = mesh.color_attributes[attribute].data[loop.index].color
        elif attribute == 'blendweights':
            data = [0, 0, 0, 0]
            for i, group in enumerate(vertex.groups):
                if i < 4:
                    data[i] = group.weight
        elif attribute == 'blendindices':
            data = [0, 0, 0, 0]
            for i, group in enumerate(vertex.groups):
                if i < 4:
                    data[i] = group.group
        else:
            data = [0, 0, 0, 0]
            if attribute in mesh.attributes:
                attr_data = mesh.attributes[attribute]
                if attr_data.data_type == 'FLOAT':
                    data[0] = attr_data.data[loop.index].value
                else:
                    data = attr_data.data[loop.index].vector
            else:
                if showWarning:
                    UIShowWarning(f"Attribute {attribute} not found in mesh data (mesh name is `{mesh.name}`)")
                data = [1, 1, 1, 1]

        # Handle cases where component_indices might be empty, meaning use the entire data
        if not component_indices:
            return data

        return [data[i] for i in component_indices]

    @staticmethod
    def packtorange(mesh, loop, vertex, matrix_transform, bake_transforms, attribute, component_indices, showWarning, data, arg1str, arg2str):
        # Default bounding vectors
        vecBoundsMin = [-1, -1, -1]
        vecBoundsMax = [1, 1, 1]
    
        # Fetch bounding vectors from mesh if available
        if arg1str and len(arg1str) > 0 and arg1str in mesh:
            vecBoundsMin = mesh[arg1str]
        
        if arg2str and len(arg2str) > 0 and arg2str in mesh:
            vecBoundsMax = mesh[arg2str]
    
        # Normalize the data to the range [0, 1]
        normalized_data = []
        for i in range(len(data)):
            min_val = vecBoundsMin[i]
            max_val = vecBoundsMax[i]
            normalized_val = (data[i] - min_val) / (max_val - min_val)
            normalized_data.append(normalized_val)
    
        def pack_values_30bit(normalized_data):
            """
            Packs the normalized data into a single 30-bit integer.
            Each value is represented using 10 bits.
            """
            if len(normalized_data) == 3:
                # Ensure the normalized values are within [0, 1] and then convert to 10-bit integers
                int_vals = [int(max(0, min(1, val)) * 1023) for val in normalized_data]
        
                # Pack three 10-bit values into a 30-bit integer
                packed_int = (
                    (int_vals[0] & 0x3FF) << 20 |
                    (int_vals[1] & 0x3FF) << 10 |
                    (int_vals[2] & 0x3FF)
                )
        
                # Convert the 30-bit integer to a 32-bit int for storage
                # Use only 30 bits, ensure the upper 2 bits are zero
                packed_value = packed_int & 0x3FFFFFFF
        
                return packed_value
            else:
                raise ValueError("Unsupported number of values to pack")

        # Pack the normalized values into a 30-bit integer
        packed_value = pack_values_30bit(normalized_data)
      
        return [packed_value]





class VertexAnimation:
    def __init__(self, name, blendermapping):
        self.name = name
        self.blendermapping = blendermapping
        self.attributes = []

    def add_attribute(self, shaderattributetype, shapefileattributename, dataformat, blendervertexmapping):
        attr = VertexAttribute(shaderattributetype, shapefileattributename, dataformat, blendervertexmapping)
        self.attributes.append(attr)


class I3D_CustomShapeAttributes:
    def __init__(self):
        self.attributes = []  # List of VertexAttribute
        self.extraattributes = []  # List of VertexAttribute
        self.vertex_animations = []  # List of VertexAnimation

    def merge(self, other):
        """
        Merge `self` into `other`.

        - Walk through `self.attributes` and `self.extraattributes` to find matching `shaderAttributeType` in `other`.
        - Walk through `self.vertex_animations` to find matching `name` in `other`.
        - Replace items in `other` or append if not present.

        Parameters:
            other (I3D_CustomShapeAttributes): The instance to merge into `self`.
        """
        if not isinstance(other, I3D_CustomShapeAttributes):
            raise TypeError("Can only merge with another I3D_CustomShapeAttributes instance.")

        # Merge attributes and extraattributes
        self._merge_items(other.attributes, self.attributes, "shader_attrib_type")
        self._merge_items(other.extraattributes, self.extraattributes, "shader_attrib_type")

        # Merge vertex animations
        self._merge_items(other.vertex_animations, self.vertex_animations, "name")

    @staticmethod
    def _merge_items(target_list, source_list, key_attr):
        """
        Merge items from `target_list` into `source_list`.

        - If an item in `target_list` matches an item in `source_list` by `key_attr`, replace it.
        - If an item in `target_list` doesn't exist in `source_list`, append it.

        Parameters:
            source_list (list): The list being merged into (modified in-place).
            target_list (list): The list of items to merge.
            key_attr (str): The attribute name used for comparison.

        Returns:
            None: Updates `source_list` in place.
        """
        for target_item in target_list:
            found = False
            for i, source_item in enumerate(source_list):
                if getattr(source_item, key_attr) == getattr(target_item, key_attr):
                    # Replace the existing source item with the target item
                    source_list[i] = target_item
                    found = True
                    break
            if not found:
                # Append the target item if it wasn't found
                source_list.append(target_item)


    def add_attribute(self, shader_attrib_type, shape_file_attrib_name, data_format, blender_vertex_mapping):
        attr = VertexAttribute(shader_attrib_type, shape_file_attrib_name, data_format, blender_vertex_mapping)
        self.attributes.append(attr)

    def add_extraattribute(self, shader_attrib_type, shape_file_attrib_name, data_format, blender_vertex_mapping):
        attr = VertexAttribute(shader_attrib_type, shape_file_attrib_name, data_format, blender_vertex_mapping)
        self.extraattributes.append(attr)

    def add_vertex_animation(self, vertex_animation):
        self.vertex_animations.append(vertex_animation)

    def hasMapping(self, meshtype, attribute_name):
        for attr in self.attributes:
            for mapping in attr.mappings:
                if mapping[0] == meshtype:
                    if (meshtype == 'shape_key' and attribute_name in mapping[2]) or (meshtype == 'mesh' and attribute_name in mapping[1]):
                        return True

        for attr in self.extraattributes:
            for mapping in attr.mappings:
                if mapping[0] == meshtype:
                    if (meshtype == 'shape_key' and attribute_name in mapping[2]) or (meshtype == 'mesh' and attribute_name in mapping[1]):
                        return True
        return False


 
    def expandVertexAnimations(self, mesh):
        expanded_animations = {}

        for anim in self.vertex_animations:
            if "Shape Key" in anim.blendermapping:
                if anim.name not in expanded_animations:
                    # Split the string by ';'
                    keyframe_entries = anim.blendermapping.split(';')

                    # Extract keyframe names from each entry
                    keyframes = []
                    for entry in keyframe_entries:
                        from_frame = entry.split('->')[1]
                        frame = {"from": from_frame, "to": None, "interpolate": 0}
                        keyframes.append(frame)

                    expanded_animations[anim.name] = {
                        "keyframes": keyframes,
                        "attributes": anim.attributes
                    }
                else:
                    print(f"{anim.name} already generated. Review expression or code.")
            elif "NLA" in anim.blendermapping:
                nla_pattern = anim.blendermapping.split("->")[1]
                nla_regex = re.compile(nla_pattern.replace("*", ".*"))

                if mesh.shape_keys:
                    shape_keys = mesh.shape_keys
                    if shape_keys.animation_data:
                        sk_animation_data = shape_keys.animation_data

                        # Process NLA tracks for shape keys
                        if sk_animation_data.nla_tracks:
                            for track in sk_animation_data.nla_tracks:
                                print(f"Shape Keys NLA Track: {track.name}")
                                if len(track.strips) == 1:
                                    strip = track.strips[0]
                                    if strip.action:
                                        action_type_result = action_type(strip.action)
                                        if action_type_result == "shape_keys":
                                            if nla_regex.match(track.name):
                                                anim_name = anim.name.replace("*", track.name)
                                                if anim_name not in expanded_animations:
                                                    unsortedkeyframes = []
                                                    # ok so you think you can use indexes but it does not work so you need to look at the data in the keyframs to see the actual frame in the timeline
                                                    for fcu in strip.action.fcurves:
                                                        keyframe = fcu.keyframe_points[0]
                                                        frame_number = keyframe.co[0]
                                                        if strip.action_frame_start <= frame_number < strip.action_frame_end:
                                                            data_path = fcu.data_path.split('[')[1].split(']')[0].strip('\"')
                                                            frame_data = {"from": data_path, "to": None, "interpolate": 0, "frame_number": frame_number}
                                                            unsortedkeyframes.append(frame_data)
                                                    if len(unsortedkeyframes) > 0:
                                                        # Sort keyframes by frame number
                                                        keyframes = sorted(unsortedkeyframes, key=lambda x: x['frame_number'])
                                                        expanded_animations[anim_name] = {
                                                            "keyframes": keyframes,
                                                            "attributes": anim.attributes
                                                        }
                                                    else:
                                                        print(f"{anim_name} no key frames found")
                                                else:
                                                    print(f"{anim_name} already generated. Review expression or code.")

        return expanded_animations


    @classmethod
    def load_from_xml(cls, xml_path):
        global g_Global_I3D_CustomShapeAttributes

        if xml_path[0] == "$":
            xml_path = bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation + xml_path[1:]

        if xml_path in g_Global_I3D_CustomShapeAttributes:
            return g_Global_I3D_CustomShapeAttributes[xml_path]

        if not os.path.isfile(xml_path):
            print('Could not find xml file! (%s)' % xmlFile)
            return None
        if not xml_path.endswith(".xml"):
            print("Selected File is not xml format: {}".format(xml_path.split("\\")[-1]))
            return None

   
        try:
            with open(xml_path, 'rb') as file:
                content = file.read()

            # Remove BOM if present
            if content.startswith(b'\xef\xbb\xbf'):
                content = content[3:]

            # Parse the XML content
            tree = ET.ElementTree(ET.fromstring(content))
            root = tree.getroot()
            instance = cls()
            for elem in root.findall('RequiredShapeAttribute'):
                attr = VertexAttribute.from_xml_element(elem)
                if attr is not None:
                    instance.attributes.append(attr)
                else:
                    print("Error: Invalid attribute in XML. Skipping.")

            for elem in root.findall('ExtraShapeAttribute'):
                attr = VertexAttribute.from_xml_element(elem)
                if attr is not None:
                    instance.extraattributes.append(attr)
                else:
                    print("Error: Invalid attribute in XML. Skipping.")
 

            for anim in root.findall('VertexAnimation'):
                vertex_animation = VertexAnimation(
                    anim.get('name'),
                    anim.get('blendermapping')
                )
                for attr in anim.findall('Attribute'):
                    vertex_animation.add_attribute(
                        attr.get('shaderattributetype'),
                        attr.get('shapefileattributename'),
                        attr.get('dataformat'),
                        attr.get('blendervertexmapping')
                    )
                instance.add_vertex_animation(vertex_animation)

            if instance.validate(None) == False:
                return None

            g_Global_I3D_CustomShapeAttributes[xml_path] = instance
            return instance
        except ET.ParseError as e:
            print(f"Error parsing XML file: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    

    def getVertexData(self , m_meshGen, vertex, m_loop, matrixTransform, bakeTransforms,showWarning):
        vertItem = {}
        if len(self.attributes) > 0 :
            vertItem["data"] = {}                
            for attr in self.attributes:
                attr.buildvertexattribute(vertItem["data"],m_meshGen, m_loop, vertex, matrixTransform, bakeTransforms,showWarning)  
        if len(self.extraattributes) > 0 :
            vertItem["extraData"] = {}                
            for attr in self.extraattributes:
                attr.buildvertexattribute(vertItem["extraData"],m_meshGen, m_loop, vertex, matrixTransform, bakeTransforms,showWarning)  

        return vertItem 

  
    def generateVertexAnimations(self, m_meshGen,originalMesh, vertexIndices, loopIndices,matrixTransform, bakeTransforms ):
        """
        This code extracts all the key frame animations given from the mesh that match up to the info in the shape definition
        it returns a structure will all the vertexAnimations. 
        The reason it works by passing in the vertex index and loop indices is because we want to just process one frame at a time
        we do this so that we do not have alot of tempory memory floating around while processing
        """

        expanded_vertex_animations = self.expandVertexAnimations(originalMesh)

        if len(expanded_vertex_animations) == 0 :
            return None


        vertexAnimations = []
        for key , anim in expanded_vertex_animations.items():
            newAnim =  { "name": key,
                    "keyframes": [],
                    "dataFormats" : {}}   

            for attr in anim["attributes"]:
                if attr.shader_attrib_type not in newAnim["dataFormats"]:
                    newAnim["dataFormats"][attr.shader_attrib_type] = attr.data_format
            showWarning = True
            for frame in anim["keyframes"]:
                VertexAttribute.clear_cache()
                newFrame = []
                for vertex, loop in zip(vertexIndices, loopIndices): 
                    vertexItem = {} 
                    for attr in anim["attributes"]:
                        attr.buildvertexattribute(vertexItem, m_meshGen, loop, vertex, matrixTransform, bakeTransforms,showWarning, frame)  
                    newFrame.append(vertexItem)
                    showWarning = False
                newAnim["keyframes"].append(newFrame)
                VertexAttribute.cleanupTangentLayers(m_meshGen)
                VertexAttribute.clear_cache()
            vertexAnimations.append(newAnim)

        return vertexAnimations
            
   
    def embedRuntimeFormats(self, vertexData ):
        if len(self.attributes) > 0 :
            if "dataFormats" not in vertexData:
                vertexData["dataFormats"] = {}

            for attr in self.attributes:
                if attr.shader_attrib_type not in vertexData["dataFormats"]:
                    vertexData["dataFormats"][attr.shader_attrib_type] = attr.data_format

        if len(self.extraattributes) > 0 :
            if "extraDataFormats" not in vertexData:
                vertexData["extraDataFormats"] = {}

            for attr in self.extraattributes:
                if attr.shader_attrib_type not in vertexData["extraDataFormats"]:
                    vertexData["extraDataFormats"][attr.shader_attrib_type] = attr.data_format

    def validate(self, mesh):
        # this function is here as a stop gap to ensure mappings are valid until the runtime can handle the 
        # full spectrum of types. 

        expected_attributes = [
            {"shaderattributetype": "position", "shapefileattributename": "p", "dataformat": "float3"},
            {"shaderattributetype": "position", "shapefileattributename": "p", "dataformat": "float3_force32bit"},
            {"shaderattributetype": "normal", "shapefileattributename": "n", "dataformat": "short4n"},
            {"shaderattributetype": "tangent", "shapefileattributename": "t", "dataformat": "short4n"},
            {"shaderattributetype": "normal", "shapefileattributename": "n", "dataformat": "32bitqt"},
            {"shaderattributetype": "uv0", "shapefileattributename": "t0", "dataformat": "short2n"},
            {"shaderattributetype": "uv1", "shapefileattributename": "t1", "dataformat": "short2n"},
            {"shaderattributetype": "uv2", "shapefileattributename": "t2", "dataformat": "short2n"},
            {"shaderattributetype": "uv3", "shapefileattributename": "t3", "dataformat": "short2n"},
            {"shaderattributetype": "color", "shapefileattributename": "c", "dataformat": "colourubyte4"},
            {"shaderattributetype": "blendweights", "shapefileattributename": "bw", "dataformat": "ubyte4n"},
            {"shaderattributetype": "blendindex", "shapefileattributename": "bi", "dataformat": "ubyte4"},
        ]

        for attribute in self.attributes:
            shaderattributetype = attribute.shader_attrib_type
            if ':' in shaderattributetype:
                shaderattributetype, specifier = shaderattributetype.split(':')
            shapefileattributename = attribute.shape_file_attrib_name
            dataformat = attribute.data_format

            valid = False
            for expected in expected_attributes:
                if (shaderattributetype == expected["shaderattributetype"] and 
                    shapefileattributename == expected["shapefileattributename"] and 
                    dataformat == expected["dataformat"]):
                    valid = True
                    break

            if not valid:
                print(f"Warning: For shaderattributetype '{shaderattributetype}', "
                      f"expected a matching shapefileattributename and dataformat, but got "
                      f"shapefileattributename '{shapefileattributename}' "
                      f"and dataformat '{dataformat}'.")
                return False

        return True



def append_vertex_item(item, result_dict):

    # lets do by hand 
    if "data" in item :
        if "data" not in result_dict :
            result_dict["data"] = []
        result_dict["data"].append(item["data"])

    if "extraData" in item :
        if "extraData" not in result_dict :
            result_dict["extraData"] = []
        result_dict["extraData"].append(item["extraData"])


def generate_custom_shape_attributes(m_meshGen, allowblendwieghts):
    attributes = []

    # Add position attribute
    if UIGetAttrBool("I3D_export32bitposition"):
        attributes.append({
            "shaderattributetype": "position",
            "shapefileattributename": "p",
            "dataformat": "float3_force32bit",
            "blendervertexmapping": "position[0:3]"
        })
    else:
        attributes.append({
            "shaderattributetype": "position",
            "shapefileattributename": "p",
            "dataformat": "float3",
            "blendervertexmapping": "position[0:3]"
        })

    if UIGetAttrBool("I3D_exportNormals"):
        if UIGetAttrBool("I3D_use32bitQT"):
            attributes.append({
                "shaderattributetype": "normal",
                "shapefileattributename": "n",
                "dataformat": "32bitqt",
                "blendervertexmapping": "normal"
            })
        else:
            attributes.append({
                "shaderattributetype": "normal",
                "shapefileattributename": "n",
                "dataformat": "short4n",
                "blendervertexmapping": "normal"
            })

    if UIGetAttrBool("I3D_exportTangents"):
        attributes.append({
            "shaderattributetype": "tangent",
            "shapefileattributename": "t",
            "dataformat": "short4n",
            "blendervertexmapping": "tangent[0:3];bitangent_sign"
        })

    if UIGetAttrBool("I3D_exportColors"):
        m_vtxColorLayerName = getRenderColorName(m_meshGen.name)
        if m_vtxColorLayerName:
            attributes.append({
                "shaderattributetype": "color",
                "shapefileattributename": "c",
                "dataformat": "colourubyte4",
                "blendervertexmapping": f"{m_vtxColorLayerName}[0:4]"
            })

    if UIGetAttrBool("I3D_exportTexCoords"):
        for m_i in range(len(m_meshGen.uv_layers)):
            if m_i == 4:
                break
            uv_map_name = m_meshGen.uv_layers[m_i].name
            attributes.append({
                "shaderattributetype": f"uv{m_i}",
                "shapefileattributename": f"t{m_i}",
                "dataformat": "short2n",
                "blendervertexmapping": f"{uv_map_name}[0:2]"
            })

    # Handle blendweights if needed
    if allowblendwieghts:
        if UIGetAttrBool("I3D_exportSkinWeigths"):
            attributes.append({
                "shaderattributetype": "blendweights",
                "shapefileattributename": "bw",
                "dataformat": "ubyte4n",
                "blendervertexmapping": "blendweights[0:4]"
            })
            attributes.append({
                "shaderattributetype": "blendindices",
                "shapefileattributename": "bi",
                "dataformat": "ubyte4",
                "blendervertexmapping": "blendindices[0:4]"
            })

    customShapeAttributes = I3D_CustomShapeAttributes()
    for attr in attributes:
        customShapeAttributes.add_attribute(
            attr["shaderattributetype"],
            attr["shapefileattributename"],
            attr["dataformat"],
            attr["blendervertexmapping"]
        )

    return customShapeAttributes



