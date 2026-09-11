import os
import bpy
import math

try:
    from lxml import etree as xml_ET
except:
    import xml.etree.cElementTree as xml_ET


def getmaterialShaderNode(materialName, node_path):
     # Get the material by name
    material = bpy.data.materials.get(materialName)
    # Check if the material exists and uses nodes
    if not material or not material.use_nodes:
        return None
    
    # Start from the material node tree's output node
    nodes = material.node_tree.nodes
    current_node = None
    
    for index, node_name in enumerate(node_path):
        if node_name in nodes:
            current_node = nodes[node_name]
            # If this node is a group, and not the last item in the path, dive into its node tree
            if index != len(node_path) - 1 : 
                if isinstance(current_node, bpy.types.ShaderNodeGroup):
                    nodes = current_node.node_tree.nodes
                else:
                    return None
            else:
                # If we're at the last item or it's not a group, we've found our node
                break
        else:
            if index == len(node_path) -1:
                if isinstance(current_node, bpy.types.ShaderNodeGroup):
                    input_socket = current_node.inputs.get(node_name)
                    if input_socket != None: 
                        return input_socket
            return None
    
    return current_node





"""
get material param
this gathers up a material param and returns it as an array 
"""

def getMaterialShaderFloatParam(materialName, paramName, expectedlen):
    returnVar = []
    
    if paramName == None:
        return None

    searchList = paramName
    if isinstance(searchList, list) == False:
        searchList = [paramName]

    for node_path in searchList:
        node = getmaterialShaderNode(materialName, node_path)
        if node != None:
            if isinstance(node, bpy.types.NodeSocket):
                # Handle the case when 'node' is a socket
                if node.is_linked:
                    # If the socket is linked, get the value from the linked node's output
                    linked_value = node.links[0].from_socket.default_value
                    # Ensure the linked value matches the expected type and length
                    if hasattr(linked_value, '__len__'):
                      returnVar = returnVar + [float(value) for value in list(linked_value)]
                    else:
                        returnVar = returnVar + [float(linked_value)]
                else:
                    # Use the default value of the socket
                    default_value = node.default_value
                    if hasattr(default_value, '__len__') and len(default_value):
                       returnVar = returnVar + [float(value) for value in default_value]
                    else:
                        returnVar = returnVar + [float(default_value)] 

            else:
                # Check all outputs for the first matching set of floats as per expectedlen
                for output in node.outputs:
                    if output.type == 'VALUE' and isinstance(output.default_value, float):
                        returnVar = returnVar + [output.default_value]
                        # If output is a vector and its length matches expectedlen, return the slice
                    elif hasattr(output.default_value, '__len__') and len(output.default_value):
                        if output.type == 'VECTOR' or output.type == 'COLOR':
                            returnVar = returnVar + list(output.default_value[:expectedlen])
            
    if len(returnVar) >= expectedlen :
        return returnVar[:expectedlen]


    return None



def find_first_texture(node):
    """Recursively searches for the first texture node in the node tree."""
    if node.type.startswith('TEX'):  # Check if the node is a texture node
        return node
    for input_socket in node.inputs:
        if input_socket.is_linked:
            linked_node = input_socket.links[0].from_node  # Get the node that outputs to this socket
            result = find_first_texture(linked_node)
            if result:
                return result
    return None

import bpy

def getMaterialShaderTextureParamFromNodeName(materialName, paramName):
    if paramName == None: 
        return None

    # Get the starting node or texture node
    starting_node_or_socket = None
    if isinstance(paramName, list):
        for node_path in paramName:
            starting_node_or_socket = getmaterialShaderNode(materialName, node_path)
            if starting_node_or_socket:
                break
    else:
        starting_node_or_socket = getmaterialShaderNode(materialName, [paramName])

    if starting_node_or_socket:
        # If the starting point is a socket, find the connected node
        if isinstance(starting_node_or_socket, bpy.types.NodeSocket):
            # Check if the socket is linked
            if not starting_node_or_socket.is_linked:
                return None  # No texture node to extract if the socket is not linked
            starting_node = starting_node_or_socket.node
        else:
            starting_node = starting_node_or_socket

        # Search for the first texture node recursively
        texture_node = find_first_texture(starting_node)
        if texture_node:
            # Extract the image filename from the texture node
            if texture_node.type == 'TEX_IMAGE' and texture_node.image:
                image_filename = bpy.path.abspath(texture_node.image.filepath)
                if image_filename == "" :
                    raise Exception("Error: export will fail with material {} and link {} because the texture path is empty".format(materialName, paramName))
 
                if bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation in image_filename:
                    image_filename = image_filename.replace(bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation, "$")
                else:
                    image_filename = bpy.path.relpath(image_filename)
                return image_filename

    return None


def getMaterialShaderBufferParamFromNodeName(materialName, paramName):
    if paramName == None: 
        return None

    # Get the starting node or texture node
    starting_node_or_socket = None
    if isinstance(paramName, list):
        for node_path in paramName:
            starting_node_or_socket = getmaterialShaderNode(materialName, node_path)
            if starting_node_or_socket:
                break
    else:
        starting_node_or_socket = getmaterialShaderNode(materialName, [paramName])

    if starting_node_or_socket:
        # If the starting point is a socket, find the connected node
        if isinstance(starting_node_or_socket, bpy.types.NodeSocket):
            # Check if the socket is linked
            if not starting_node_or_socket.is_linked:
                return None  # No texture node to extract if the socket is not linked
            starting_node = starting_node_or_socket.node
        else:
            starting_node = starting_node_or_socket

        # Search for the first texture node recursively
        texture_node = find_first_texture(starting_node)
        if texture_node:
            # Extract the image filename from the texture node
            if texture_node.type == 'TEX_IMAGE' and texture_node.image:
                image_filename = bpy.path.abspath(texture_node.image.filepath)
                if bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation in image_filename:
                    image_filename = image_filename.replace(bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation, "$")
                else:
                    image_filename = bpy.path.relpath(image_filename)
                return image_filename

    return None


def getMaterialShaderTextureParamFromLinkInputNames(materialName, paramNames):
    if materialName not in bpy.data.materials:
        return None

    mat = bpy.data.materials[materialName]
    if not mat.use_nodes:
        return None

    nodes = mat.node_tree.nodes
    output_node = next((node for node in nodes if node.type == 'OUTPUT_MATERIAL'), None)
    if not output_node:
        return None

    surface_socket = output_node.inputs['Surface']
    if not surface_socket.is_linked:
        return None

    surface_node = surface_socket.links[0].from_node

    # Go through each paramName looking for matches in the node inputs
    for paramName in paramNames:
        linked_node = None
        # Find the matching input by name and check if it's linked
        for input_socket in surface_node.inputs:
            if input_socket.name == paramName and input_socket.is_linked:
                linked_node = input_socket.links[0].from_node
                break

        if linked_node is None:
            #print(f"No linked input found for {paramName}")
            continue  # Skip to next paramName if no link found

        textureNode = find_first_texture(linked_node)
        if textureNode and textureNode.type == 'TEX_IMAGE' and textureNode.image:
            image_filename = bpy.path.abspath(textureNode.image.filepath)
            if bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation in image_filename:
                image_filename = image_filename.replace(bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation, "$")
           #return the image file name... 
            else:
                #get the relative filename 
                image_filename = bpy.path.relpath(image_filename)
            return image_filename
        #else:
        #    print(f"Texture not found for {paramName}")

    return None





g_shaderDataCache = {}

def extractXMLShaderData(xmlFile):
    """
    Extracts the data from the specified file

    :returns: a dictionary with keys: parameters, textures and variations according
    to the data contained in the file
    :returns: None if file is not valid
    """
    if xmlFile[0] == "$":
        xmlFile = bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation + xmlFile[1:]

    if xmlFile in g_shaderDataCache:
        return g_shaderDataCache[xmlFile]

    if not os.path.isfile(xmlFile):
        #print('Could not find xml file! (%s)' % xmlFile)
        return None
    if not xmlFile.endswith(".xml"):
        print("Selected File is not xml format: {}".format(xmlFile.split("\\")[-1]))
        return None

    file = open(xmlFile, 'rb')
    if file is None:
        print('Could not find xml file! (%s)' % xmlFile)
        return None
    xmlTree = xml_ET.parse(file)
    file.close()

    variations, variations_groups = getVariationsFromShaderFile(xmlTree.getroot())
    parameterTemplates = getParameterTemplatesFromShaderFile(xmlTree.getroot())
    textures, textures_group = getTextureFromShaderFile(xmlTree.getroot(), parameterTemplates)
    buffers, buffers_group = getBufferFromShaderFile(xmlTree.getroot(), parameterTemplates)
    defaultTextures = getDefaultTexturesFromShaderFile(xmlTree.getroot())
    parameters, parameters_group , parameters_type = getParametersFromShaderFile(xmlTree.getroot(), parameterTemplates)
    shaderData = {"parameters" : parameters, "textures" : textures, "buffers" : buffers, "variations" : variations, "parameters_group" : parameters_group, "textures_group" : textures_group, "buffers_group" : buffers_group, "variations_groups" : variations_groups, "parameterTemplates" : parameterTemplates, "parameterTypes" : parameters_type, 
                  "defaultTextures" : defaultTextures}

    g_shaderDataCache[xmlFile] = shaderData

    return shaderData

def getParametersFromShaderFile(xmlRoot, parameterTemplatesDict):
    """Extracts the name and default value from Parameters"""

    parameterDict = {}
    parameterGroupDict = {}
    parameterTypeDict = {}
    currentLine = 0

    parameters = xmlRoot.find("Parameters")
    if parameters:
        for parameter in parameters.findall("Parameter"):
            name = parameter.get("name")
            value = parameter.get("defaultValue")
            val_type = parameter.get("type")
            group = parameter.get("group")
            template = parameter.get("template")
    
            if template and template not in parameterTemplatesDict:
                #TODO(jdellsperger): Bleet about malformed xml?
                parameterTemplatesDict[template] = {'filename': '', 'parameters': {}}

            # if arraySize set the following lines are <Default index="0">value</Default>
            arraySize = parameter.get("arraySize")
            if arraySize and name:
                for defaultElement in parameter.findall("Default"):
                    indexDft = defaultElement.get("index")
                    valueDft = defaultElement.text
                    if indexDft and valueDft:
                        if template:
                            parameterTemplatesDict[template]["parameters"][name + indexDft] = valueDft
                        else:
                            parameterDict[name + indexDft] = valueDft
                        if group is not None:
                            parameterGroupDict[name + indexDft] = group
            if name and value:
                if template:
                    parameterTemplatesDict[template]["parameters"][name] = value
                else:
                    parameterDict[name] = value
                if group is not None:
                    parameterGroupDict[name] = group
                if val_type is not None:
                    parameterTypeDict[name] = val_type

            elif name and val_type:
                #defined type but no default values specified
                val_type_str = val_type
                val = None
                if val_type_str == 'float4':
                    val = "1 1 1 1"
                elif val_type_str == 'float3':
                    val = "1 1 1"
                elif val_type_str == 'float2':
                    val = "1 1"
                elif val_type_str == 'float':
                    val = "1"
                if val:
                    if template:
                        parameterTemplatesDict[template]["parameters"][name] = val
                    else:
                        parameterDict[name] = val
                    if group is not None:
                        parameterGroupDict[name] = group
                    if val_type is not None:
                        parameterTypeDict[name] = val_type

        currentLine = currentLine + 1
    return parameterDict, parameterGroupDict, parameterTypeDict

def getDefaultTexturesFromShaderFile( xmlRoot):
    """Extracts the names that we want
    the idea of this function is to simply work out what default textures we want 
    there is 4 of them
    in theory what we should to is look at the code and see if at any point we call for the code for accessing the maps to be undefined however 
    we are not really in position to that at this point ... yet 
    so the approach taken is to leverage the uvusages and gather in what items are used. 
    """

    # 
    defaultitemssearch = {
    "Texture": {"uvUsage" : "baseMap", "codesearch": "ALBEDO_MAP", "nodename": "Base Color", "inputlinks": ["Base Color","Albedo"]},
    "Normalmap": {"uvUsage" : "normalMap","codesearch": "NORMAL_MAP", "nodename": "Normalmap", "inputlinks": ["Normal"]},
    "Glossmap": {"uvUsage" : "glossMap","codesearch": "GLOSS_MAP", "nodename": "Glossmap", "inputlinks": ["Specular", "Roughness","ORM"]},
    "Emissivemap": {"uvUsage" : "emissivemap","codesearch": "EMISSIVE_MAP", "nodename": "Emissivemap", "inputlinks": ["Emission"]},
    }

    defaultTextures = {}

    usages = xmlRoot.find("UvUsages")
    for usage in usages.findall("UvUsage"):
        name = usage.get("textureName")
        for key, value in defaultitemssearch.items():
            if name == value["uvUsage"]:
                defaultTextures[key] = value
                break;

    return defaultTextures


def getTextureFromShaderFile(xmlRoot, parameterTemplatesDict):
    """Extracts the name and default file name from Texture"""

    textureDict = {}
    textureGroupDict = {}
 
    textures = xmlRoot.find("Textures")
    if textures:
        for texture in textures.findall("Texture"):
            name = texture.get("name")
            value = texture.get("defaultFilename")
            group = texture.get("group")
            template = texture.get("template")
 
            if template and template not in parameterTemplatesDict:
                #TODO(jdellsperger): Bleet about malformed xml?
                parameterTemplatesDict[template] = {'filename': '', 'textures': {}}

            if not value:
                value = ""

            if name:
                if template:
                    parameterTemplatesDict[template]["textures"][name] = value
                else:
                    textureDict[name] = value
                textureGroupDict[name] = group
  

    return textureDict, textureGroupDict 




def getBufferFromShaderFile(xmlRoot, parameterTemplatesDict):
    """Extracts the name and default file name from Buffer"""

    bufferDict = {}
    bufferGroupDict = {}
 
    buffers = xmlRoot.find("Buffers")
    if buffers:
        for buffer in buffers.findall("Buffer"):
            name = buffer.get("name")
            value = buffer.get("defaultFilename")
            group = buffer.get("group")
            template = buffer.get("template")
 
            if template and template not in parameterTemplatesDict:
                #TODO(jdellsperger): Bleet about malformed xml?
                parameterTemplatesDict[template] = {'filename': '', 'buffers': {}}

            if not value:
                value = ""

            if name:
                if template:
                    parameterTemplatesDict[template]["buffers"][name] = value
                else:
                    bufferDict[name] = value
                bufferGroupDict[name] = group
  

    return bufferDict, bufferGroupDict 


def getVariationsFromShaderFile(xmlRoot):
    """Extracts the name from Variation"""

    variationDict = {}
    variationGroupsDict = {}

    variations = xmlRoot.find("Variations")
    if variations:
        for variation in variations.findall("Variation"):
            groups = variation.get("groups")
            name = variation.get("name")
            variationDict[name] = name
            variationGroupsDict[name] = groups

    return variationDict, variationGroupsDict

def getParameterTemplatesFromShaderFile(xmlRoot):
    parameterTemplatesDict = {}
    parameterTemplates = xmlRoot.find("ParameterTemplates")
    if parameterTemplates:
        for parameterTemplate in parameterTemplates.findall("ParameterTemplate"):
            parameterTemplateId = parameterTemplate.get("id")
            parameterTemplateFilename = parameterTemplate.get("filename")

            parameterTemplatesDict[parameterTemplateId] = {'filename': parameterTemplateFilename, 'parameters': {}, 'textures': {}, 'subtemplates': {}}

            if parameterTemplateFilename is not None:
                tree = None
                try:
                    templatesXmlFilename = parameterTemplateFilename.replace("$", bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation)
                    tree = xml_ET.parse(templatesXmlFilename)
                except xml_ET.ParseError as err:
                    print("Failed to load parameter templates from '%s': %s" % (templatesXmlFilename, err))
                else:
                    templatesFileRoot = tree.getroot()
                    parameterTemplatesDict[parameterTemplateId]["name"] = templatesFileRoot.get("name")
                    parameterTemplatesDict[parameterTemplateId]["rootSubTemplateId"] = templatesFileRoot.get("id")

                # Parse the templates xml file.
                while tree is not None:
                    templatesFileRoot = tree.getroot()
                    parentTemplateFilename = templatesFileRoot.get("parentTemplateFilename")
                    parentTree = None
                    parentId = None
                    if parentTemplateFilename is not None:
                        try:
                            templatesXmlFilename = parentTemplateFilename.replace("$", bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation)
                            parentTree = xml_ET.parse(templatesXmlFilename)
                        except xml_ET.ParseError as err:
                            print("Failed to load parameter templates from '%s': %s" % (templatesXmlFilename, err))
                        else:
                            parentTemplatesFileRoot = parentTree.getroot()
                            parentId = parentTemplatesFileRoot.get("id")
                    defaultParentTemplate = templatesFileRoot.get("parentTemplateDefault")
                    subTemplateId = templatesFileRoot.get("id")
                    parameterTemplatesDict[parameterTemplateId]["subtemplates"][subTemplateId] = {'name': templatesFileRoot.get("name"), 'parentId': parentId, 'defaultParentTemplate': defaultParentTemplate, 'templates': {}}
                    for template in templatesFileRoot.findall("template"):
                        name = template.get("name")
                        parameterTemplatesDict[parameterTemplateId]["subtemplates"][subTemplateId]['templates'][name] = {}
                        attributes = template.attrib
                        del attributes["name"]
                        for attr in attributes:
                            parameterTemplatesDict[parameterTemplateId]["subtemplates"][subTemplateId]['templates'][name][attr] = template.get(attr)
                    tree = parentTree

            #print("Parameter template {}, {}".format(parameterTemplateId, parameterTemplateFilename))
    return parameterTemplatesDict

g_paramaterMappingDataCache = {}

def extractXMLParamaterMappingData(xmlFile):
    """
    Extracts the data from the specified file

    :returns: a dictionary with keys: parameters, textures and variations according
    to the data contained in the file
    :returns: None if file is not valid
    """
    if xmlFile[0] == "$":
        xmlFile = bpy.context.scene.I3D_UIexportSettings.I3D_gameLocation + xmlFile[1:]

    if xmlFile in g_paramaterMappingDataCache:
        return g_paramaterMappingDataCache[xmlFile]

    if not os.path.isfile(xmlFile):
        #print('Could not find xml file! (%s)' % xmlFile)
        return None
    if not xmlFile.endswith(".xml"):
        print("Selected File is not xml format: {}".format(xmlFile.split("\\")[-1]))
        return None
    
    file = open(xmlFile, 'rb')
    if file is None:
        print('Could not find xml file! (%s)' % xmlFile)
        return None
    xmlTree = xml_ET.parse(file)
    file.close()

    textureblenderMaterialLinkDict = getTextureMappingsFromShaderFile(xmlTree.getroot())
    bufferblenderMaterialLinkDict = getBufferMappingsFromShaderFile(xmlTree.getroot())
    paramatersblenderMaterialLinkDict = getParameterMappingsFromShaderFile(xmlTree.getroot())
    mappingData = {"textureblenderMaterialLinkDict" : textureblenderMaterialLinkDict, "bufferblenderMaterialLinkDict" : bufferblenderMaterialLinkDict , "paramatersblenderMaterialLinkDict" : paramatersblenderMaterialLinkDict }

    g_paramaterMappingDataCache[xmlFile] = mappingData

    return mappingData

def getTextureMappingsFromShaderFile(xmlRoot):
    """Extracts the name and default file name from Texture"""
    blenderMaterialLinkDict = {}

    textures = xmlRoot.find("Textures")
    if textures:
        for texture in textures.findall("Texture"):
            name = texture.get("name")
            blenderMaterialLink = texture.get("blenderMaterialLink")

            if name:
                # ok lets setup a way to be able to tunnel into the shader node graphs and get values from it. 
                if blenderMaterialLink is not None and blenderMaterialLink != "" :
                    # Split the input string into groups separated by ';'
                    searchgroups = blenderMaterialLink.split(';')
                    # Further split each group into sub-items separated by '->'
                    searchItems = [searchgroup.split('->') for searchgroup in searchgroups]
                    blenderMaterialLinkDict[name] = searchItems

    return blenderMaterialLinkDict


def getBufferMappingsFromShaderFile(xmlRoot):
    """Extracts the name and default file name from Texture"""
    blenderMaterialLinkDict = {}

    buffers = xmlRoot.find("Buffers")
    if buffers:
        for buffer in buffers.findall("Buffer"):
            name = buffer.get("name")
            blenderMaterialLink = buffer.get("blenderMaterialLink")

            if name:
                # ok lets setup a way to be able to tunnel into the shader node graphs and get values from it. 
                if blenderMaterialLink is not None and blenderMaterialLink != "" :
                    # Split the input string into groups separated by ';'
                    searchgroups = blenderMaterialLink.split(';')
                    # Further split each group into sub-items separated by '->'
                    searchItems = [searchgroup.split('->') for searchgroup in searchgroups]
                    blenderMaterialLinkDict[name] = searchItems

    return blenderMaterialLinkDict


def getParameterMappingsFromShaderFile(xmlRoot):
    """Extracts the name and default value from Parameters"""

    blenderMaterialLinkDict = {}
 
    parameters = xmlRoot.find("Parameters")
    if parameters:
        for parameter in parameters.findall("Parameter"):
            name = parameter.get("name")
            blenderMaterialLink = parameter.get("blenderMaterialLink")

            # ok lets setup a way to be able to tunnel into the shader node graphs and get values from it. 
            if blenderMaterialLink is not None and blenderMaterialLink != "" :
                # Split the input string into groups separated by ';'
                searchgroups = blenderMaterialLink.split(';')
                # Further split each group into sub-items separated by '->'
                searchItems = [searchgroup.split('->') for searchgroup in searchgroups]
                blenderMaterialLinkDict[name] = searchItems

    return blenderMaterialLinkDict