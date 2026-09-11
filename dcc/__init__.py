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

from .. import DCC_PLATFORM as DCC_PLATFORM

if   "houdini" == DCC_PLATFORM:
    from . import dccHoudini as dcc
elif "blender" == DCC_PLATFORM:
    from . import dccBlender as dcc
    import bpy

#-------------------------------------------------------------------------------
#   Globals and Defaults
#-------------------------------------------------------------------------------
TYPE_BOOL   = 1
TYPE_INT    = 2
TYPE_FLOAT  = 3
TYPE_STRING = 4
TYPE_STRING_UINT = 5
TYPE_ENUM = 6

UINT_MAX_AS_STRING = '4294967295'
FLOAT_PRECISION = 3

SETTINGS_ATTRIBUTES = {}
SETTINGS_ATTRIBUTES['I3D_lockedGroup']          = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_static']               = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_dynamic']              = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_kinematic']            = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_compound']             = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_compoundChild']        = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_collision']            = {'type':TYPE_BOOL,  'defaultValue':True,  'i3dDefaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_collisionFilterGroup'] = {'type':TYPE_INT,   'defaultValue':0,     'i3dDefaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_collisionFilterMask']  = {'type':TYPE_INT,   'defaultValue':0,     'i3dDefaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_collisionFilterPreset']= {'type':TYPE_STRING,'defaultValue':"-",   'i3dDefaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_solverIterationCount'] = {'type':TYPE_INT,   'defaultValue':4      }
SETTINGS_ATTRIBUTES['I3D_restitution']          = {'type':TYPE_FLOAT, 'defaultValue':0      }
SETTINGS_ATTRIBUTES['I3D_staticFriction']       = {'type':TYPE_FLOAT, 'defaultValue':0.5    }
SETTINGS_ATTRIBUTES['I3D_dynamicFriction']      = {'type':TYPE_FLOAT, 'defaultValue':0.5    }
SETTINGS_ATTRIBUTES['I3D_linearDamping']        = {'type':TYPE_FLOAT, 'defaultValue':0.0    }
SETTINGS_ATTRIBUTES['I3D_angularDamping']       = {'type':TYPE_FLOAT, 'defaultValue':0.01   }
SETTINGS_ATTRIBUTES['I3D_density']              = {'type':TYPE_FLOAT, 'defaultValue':1.0    }
SETTINGS_ATTRIBUTES['I3D_ccd']                  = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_trigger']              = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_splitType']            = {'type':TYPE_INT,   'defaultValue':0      }
SETTINGS_ATTRIBUTES['I3D_splitMinU']            = {'type':TYPE_FLOAT, 'defaultValue':0.0    }
SETTINGS_ATTRIBUTES['I3D_splitMinV']            = {'type':TYPE_FLOAT, 'defaultValue':0.0    }
SETTINGS_ATTRIBUTES['I3D_splitMaxU']            = {'type':TYPE_FLOAT, 'defaultValue':1.0    }
SETTINGS_ATTRIBUTES['I3D_splitMaxV']            = {'type':TYPE_FLOAT, 'defaultValue':1.0    }
SETTINGS_ATTRIBUTES['I3D_splitUvWorldScale']    = {'type':TYPE_FLOAT, 'defaultValue':1.0    }
SETTINGS_ATTRIBUTES['I3D_joint']                = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_projection']           = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_projDistance']         = {'type':TYPE_FLOAT, 'defaultValue':0.01   }
SETTINGS_ATTRIBUTES['I3D_projAngle']            = {'type':TYPE_FLOAT, 'defaultValue':0.01   }
SETTINGS_ATTRIBUTES['I3D_xAxisDrive']           = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_yAxisDrive']           = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_zAxisDrive']           = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_drivePos']             = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_driveForceLimit']      = {'type':TYPE_FLOAT, 'defaultValue':100000 }
SETTINGS_ATTRIBUTES['I3D_driveSpring']          = {'type':TYPE_FLOAT, 'defaultValue':1.0    }
SETTINGS_ATTRIBUTES['I3D_driveDamping']         = {'type':TYPE_FLOAT, 'defaultValue':0.01   }
SETTINGS_ATTRIBUTES['I3D_breakableJoint']       = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_jointBreakForce']      = {'type':TYPE_FLOAT, 'defaultValue':0.0    }
SETTINGS_ATTRIBUTES['I3D_jointBreakTorque']     = {'type':TYPE_FLOAT, 'defaultValue':0.0    }
SETTINGS_ATTRIBUTES['I3D_oc']                   = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_castsShadows']         = {'type':TYPE_BOOL,  'defaultValue':True,  'i3dDefaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_receiveShadows']       = {'type':TYPE_BOOL,  'defaultValue':True,  'i3dDefaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_renderedInViewports']  = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_ATTRIBUTES['I3D_renderedInEnvmap']     = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_grassMetaDataProvider']     = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_grassMesh']            = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_highdDetailMesh']      = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_nonRenderable']        = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_clipDistance']         = {'type':TYPE_FLOAT, 'defaultValue':0      }
SETTINGS_ATTRIBUTES['I3D_objectMask']           = {'type':TYPE_INT,   'defaultValue':255    }
SETTINGS_ATTRIBUTES['I3D_navMeshMask']          = {'type':TYPE_INT,   'defaultValue':0      }
SETTINGS_ATTRIBUTES['I3D_doubleSided']          = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_decalLayer']           = {'type':TYPE_INT,   'defaultValue':0      }
SETTINGS_ATTRIBUTES['I3D_mergeGroup']           = {'type':TYPE_INT,   'defaultValue':0      }
SETTINGS_ATTRIBUTES['I3D_mergeGroupRoot']       = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_boundingVolume']       = {'type':TYPE_STRING,'defaultValue':"" }

SETTINGS_ATTRIBUTES['I3D_softShadowsLightSize']       = {'type':TYPE_FLOAT, 'defaultValue':0.05 }
SETTINGS_ATTRIBUTES['I3D_softShadowsLightDistance']   = {'type':TYPE_FLOAT, 'defaultValue':15 }
SETTINGS_ATTRIBUTES['I3D_softShadowsDepthBiasFactor'] = {'type':TYPE_FLOAT, 'defaultValue':5 }
SETTINGS_ATTRIBUTES['I3D_softShadowsMaxPenumbraSize'] = {'type':TYPE_FLOAT, 'defaultValue':0.5 }
SETTINGS_ATTRIBUTES['I3D_iesProfileFile']             = {'type':TYPE_STRING, 'defaultValue':"" }

SETTINGS_ATTRIBUTES['I3D_terrainDecal']         = {'type':TYPE_BOOL, 'defaultValue':False }
SETTINGS_ATTRIBUTES['I3D_cpuMesh']              = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_mergeChildren']                    = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_mergeChildrenFreezeRotation']      = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_mergeChildrenFreezeTranslation']   = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_mergeChildrenFreezeScale']         = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_objectDataFilePath']   = {'type':TYPE_STRING,  'defaultValue':""  }

SETTINGS_ATTRIBUTES['I3D_selectedPredefined']   = {'type':TYPE_STRING,'defaultValue':""}
SETTINGS_ATTRIBUTES['I3D_predefHasChanged']     = {'type':TYPE_BOOL,  'defaultValue':False}


SETTINGS_ATTRIBUTES['I3D_lod']                  = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_lod1']                 = {'type':TYPE_FLOAT, 'defaultValue':0      }
SETTINGS_ATTRIBUTES['I3D_lod2']                 = {'type':TYPE_FLOAT, 'defaultValue':0      }
SETTINGS_ATTRIBUTES['I3D_lod3']                 = {'type':TYPE_FLOAT, 'defaultValue':0      }
SETTINGS_ATTRIBUTES['I3D_lodBlending']          = {'type':TYPE_BOOL, 'defaultValue':True      }
SETTINGS_ATTRIBUTES['I3D_alphaBlending']        = {'type':TYPE_BOOL,  'defaultValue':False   }
SETTINGS_ATTRIBUTES['I3D_vertexCompressionRange'] = {'type': TYPE_STRING, 'defaultValue':'Auto'}

SETTINGS_ATTRIBUTES['I3D_minuteOfDayStart']             = {'type':TYPE_INT,   'defaultValue':0 }
SETTINGS_ATTRIBUTES['I3D_minuteOfDayEnd']               = {'type':TYPE_INT,   'defaultValue':0 }
SETTINGS_ATTRIBUTES['I3D_dayOfYearStart']               = {'type':TYPE_INT,   'defaultValue':0 }
SETTINGS_ATTRIBUTES['I3D_dayOfYearEnd']                 = {'type':TYPE_INT,   'defaultValue':0 }
SETTINGS_ATTRIBUTES['I3D_weatherMask']                  = {'type':TYPE_STRING_UINT,'defaultValue':'0' }
SETTINGS_ATTRIBUTES['I3D_viewerSpacialityMask']         = {'type':TYPE_STRING_UINT,'defaultValue':'0' }
SETTINGS_ATTRIBUTES['I3D_weatherPreventMask']           = {'type':TYPE_STRING_UINT,'defaultValue':'0' }
SETTINGS_ATTRIBUTES['I3D_viewerSpacialityPreventMask']  = {'type':TYPE_STRING_UINT,'defaultValue':'0' }
SETTINGS_ATTRIBUTES['I3D_renderInvisible']              = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_visibleShaderParam']           = {'type':TYPE_FLOAT, 'defaultValue':1.0    }
SETTINGS_ATTRIBUTES['I3D_forceVisibilityCondition']     = {'type':TYPE_BOOL,  'defaultValue':False  }

SETTINGS_ATTRIBUTES['I3D_objectDataHierarchicalSetup']      = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_objectDataHideFirstAndLastObject'] = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_objectDataExportPosition']         = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_objectDataExportOrientation']      = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_ATTRIBUTES['I3D_objectDataExportScale']            = {'type':TYPE_BOOL,  'defaultValue':False  }

SETTINGS_UI = {}
# SETTINGS_UI['I3D_exportIK']                     = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_UI['I3D_exportAnimation']              = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_exportShapes']                 = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_exportNurbsCurves']            = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_UI['I3D_exportLights']                 = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_exportCameras']                = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_binaryFiles']                = {'type':TYPE_BOOL,  'defaultValue':True   }
# SETTINGS_UI['I3D_exportParticleSystems']        = {'type':TYPE_BOOL,  'defaultValue':False  }
SETTINGS_UI['I3D_exportUserAttributes']         = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_export32bitposition']          = {'type':TYPE_BOOL,  'defaultValue':False   }
SETTINGS_UI['I3D_exportNormals']                = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_use32bitQT']                   = {'type':TYPE_BOOL,  'defaultValue':False   }
SETTINGS_UI['I3D_exportTangents']               = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_exportTangentsBinaryRecalc']   = {'type':TYPE_BOOL,  'defaultValue':False   }
SETTINGS_UI['I3D_exportColors']                 = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_exportTexCoords']              = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_exportTexCoordsUVDensity']     = {'type':TYPE_BOOL,  'defaultValue':False   }

SETTINGS_UI['I3D_exportSkinWeigths']            = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_exportMergeGroups']            = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_exportVerbose']                = {'type':TYPE_BOOL,  'defaultValue':True   }

SETTINGS_UI['I3D_UImaxMeshSizeX']                = {'type':TYPE_FLOAT,  'defaultValue':0   }
SETTINGS_UI['I3D_UImaxMeshSizeY']                = {'type':TYPE_FLOAT,  'defaultValue':0   }
SETTINGS_UI['I3D_UImaxMeshSizeZ']                = {'type':TYPE_FLOAT,  'defaultValue':0   }


SETTINGS_UI['I3D_UIexportCopyFiles']          = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_exportRelativePaths']          = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_exportGameRelativePath']          = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_exportUseSoftwareFileName']    = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_updateXMLOnExport']    = {'type':TYPE_BOOL,  'defaultValue':True   }
SETTINGS_UI['I3D_exportFileLocation']           = {'type':TYPE_STRING,'defaultValue':''     }
SETTINGS_UI['I3D_shaderFolderLocation']           = {'type':TYPE_STRING,'defaultValue':''     }
SETTINGS_UI['I3D_nodeName']                     = {'type':TYPE_STRING,'defaultValue':''     }
SETTINGS_UI['I3D_nodeIndex']                    = {'type':TYPE_STRING,'defaultValue':''     }
SETTINGS_UI['I3D_updateXMLFilePath'] =          {'type':TYPE_STRING,'defaultValue':''     }


SETTINGS_PREDEFINE_PHYSIC = {"NONE":{'name':'','isPhyiscObject':True,'attributeValues':{}},
                            "VEHICLE_COMPOUND" : {'name': 'Vehicle - Compound',               'isPhyiscObject':True,  'attributeValues':{'I3D_static':False, 'I3D_dynamic':True,  'I3D_kinematic':False, 'I3D_compound':True,  'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':True, 'I3D_clipDistance':300.0, 'I3D_nonRenderable':True, 'I3D_doubleSided':False, 'I3D_decalLayer': 0, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}},
                            "VEHICLE_COMPOUND_CHILD" : {'name': 'Vehicle - CompoundChild',    'isPhyiscObject':True, 'attributeValues':{'I3D_static':False, 'I3D_dynamic':False, 'I3D_kinematic':False, 'I3D_compound':False, 'I3D_compoundChild':True, 'I3D_trigger':False,
                                                                                                    'I3D_collision':True, 'I3D_clipDistance':0.0, 'I3D_nonRenderable':True, 'I3D_doubleSided':False, 'I3D_decalLayer': 0, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 0.001, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}},
                            "STATIC_OBJECT" :{'name': 'Static Object',                                              'isPhyiscObject':True,'attributeValues':{'I3D_static':True, 'I3D_dynamic':False, 'I3D_kinematic':False,'I3D_compound':False,  'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':True, 'I3D_clipDistance':0.0,'I3D_nonRenderable':False, 'I3D_doubleSided':False, 'I3D_decalLayer': 0, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}}
                            }
SETTINGS_PREDEFINE_NON_PHYSIC = {"NONE":{'name':'','isPhyiscObject':False, 'attributeValues':{}},
                            "LIGHTS_REAL":{'name': 'Lights -  Real',    'isPhyiscObject':False, 'attributeValues':{'I3D_static':False, 'I3D_dynamic':False, 'I3D_kinematic':False, 'I3D_compound':False, 'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':False, 'I3D_clipDistance':75.0,  'I3D_nonRenderable':False, 'I3D_doubleSided':False, 'I3D_decalLayer': 0, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False , 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}},
                            "LIGHTS_CORONAS":{'name': 'Lights -  Coronas',  'isPhyiscObject':False, 'attributeValues':{'I3D_static':False, 'I3D_dynamic':False, 'I3D_kinematic':False, 'I3D_compound':False, 'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':False, 'I3D_clipDistance':200.0, 'I3D_nonRenderable':False, 'I3D_doubleSided':False, 'I3D_decalLayer': 0, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}},
                            "LIGHTS_STATIC":{'name': 'Lights -  Static',   'isPhyiscObject':False, 'attributeValues':{'I3D_static':False, 'I3D_dynamic':False, 'I3D_kinematic':False, 'I3D_compound':False, 'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':False, 'I3D_clipDistance':200.0, 'I3D_nonRenderable':False, 'I3D_doubleSided':False, 'I3D_decalLayer': 0, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}},
                            "DECALS_SMALL":{'name': 'Decals - Small',       'isPhyiscObject':False, 'attributeValues':{'I3D_static':False, 'I3D_dynamic':False, 'I3D_kinematic':False, 'I3D_compound':False, 'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':False, 'I3D_clipDistance':30.0,  'I3D_nonRenderable':False, 'I3D_doubleSided':False, 'I3D_decalLayer': 1, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}},
                            "DECALS_BIG":{'name': 'Decals - Big',           'isPhyiscObject':False, 'attributeValues':{'I3D_static':False, 'I3D_dynamic':False, 'I3D_kinematic':False, 'I3D_compound':False, 'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':False, 'I3D_clipDistance':50.0,  'I3D_nonRenderable':False, 'I3D_doubleSided':False, 'I3D_decalLayer': 1, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}},
                            "EXTERIOR":{'name': 'Exterior',                 'isPhyiscObject':False, 'attributeValues':{'I3D_static':False, 'I3D_dynamic':False, 'I3D_kinematic':False, 'I3D_compound':False, 'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':False, 'I3D_clipDistance':300.0, 'I3D_nonRenderable':False, 'I3D_doubleSided':False, 'I3D_decalLayer': 0, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}},
                            "INTERIOR":{'name': 'Interior',                 'isPhyiscObject':False, 'attributeValues':{'I3D_static':False, 'I3D_dynamic':False, 'I3D_kinematic':False, 'I3D_compound':False, 'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':False, 'I3D_clipDistance':75.0,  'I3D_nonRenderable':False, 'I3D_doubleSided':False, 'I3D_decalLayer': 0, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}},
                            "INDOOR_HUD":{'name': 'IndoorHud',              'isPhyiscObject':False, 'attributeValues':{'I3D_static':False, 'I3D_dynamic':False, 'I3D_kinematic':False, 'I3D_compound':False, 'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':False, 'I3D_clipDistance':20.0,  'I3D_nonRenderable':False, 'I3D_doubleSided':False, 'I3D_decalLayer': 0, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}},
                            "MIRRORS":{'name': 'Mirrors',                   'isPhyiscObject':False, 'attributeValues':{'I3D_static':False, 'I3D_dynamic':False, 'I3D_kinematic':False, 'I3D_compound':False, 'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':False, 'I3D_clipDistance':20.0,  'I3D_nonRenderable':False, 'I3D_doubleSided':False, 'I3D_decalLayer': 1, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}},
                            "WINDOWS_INSIDE":{'name': 'WindowsInside',      'isPhyiscObject':False, 'attributeValues':{'I3D_static':False, 'I3D_dynamic':False, 'I3D_kinematic':False, 'I3D_compound':False, 'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':False, 'I3D_clipDistance':20.0,  'I3D_nonRenderable':False, 'I3D_doubleSided':False, 'I3D_decalLayer': 0, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}},
                            "WINDOWS_OUTSIDE":{'name': 'WindowsOutside',    'isPhyiscObject':False, 'attributeValues':{'I3D_static':False, 'I3D_dynamic':False, 'I3D_kinematic':False, 'I3D_compound':False, 'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':False, 'I3D_clipDistance':200.0, 'I3D_nonRenderable':False, 'I3D_doubleSided':False, 'I3D_decalLayer': 0, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}},
                            "OFF_TRACK_TREE":{'name': 'OffTrackTree',       'isPhyiscObject':False, 'attributeValues':{'I3D_static':False, 'I3D_dynamic':False, 'I3D_kinematic':False, 'I3D_compound':False, 'I3D_compoundChild':False, 'I3D_trigger':False,
                                                                                                    'I3D_collision':False, 'I3D_clipDistance':2000.0, 'I3D_nonRenderable':False, 'I3D_doubleSided':False, 'I3D_decalLayer': 0, 'I3D_terrainDecal':False, 'I3D_cpuMesh':False, 'I3D_density': 1.0, 'I3D_castsShadows':True, 'I3D_receiveShadows':True, 'I3D_renderedInViewports':True, 'I3D_renderedInEnvmap':False, 'I3D_grassMetaDataProvider':False, 'I3D_grassMesh':False, 'I3D_highdDetailMesh':False}}
                            }

#-------------------------------------------------------------------------------
#   UI
#-------------------------------------------------------------------------------
def UIgetPredefinePhysicItems(self,context):
    """ Returns a formatted Tuple of the predefined Physics Item Names """

    enumTup = tuple()
    for key, item in SETTINGS_PREDEFINE_PHYSIC.items():
        enumTup= enumTup + ((key,item['name'],""),)
    return enumTup

# def UIgetPredefinePhsysicItemsEnum(self,context):
#     return UIgetPredefinePhysicItems(self,context) + (('NONE',"",""),)

def I3DgetPredefinePhysicAttr(itemName):
    """ Returns a formatted Tuple of the predefined Physics Item Attributes """

    return SETTINGS_PREDEFINE_PHYSIC[itemName]['attributeValues']

def UIgetPredefineNonPhysicItems(self,context):
    """ Returns a formatted Tuple of the predefined non Physics Item Names """

    enumTup = tuple()
    for key, item in SETTINGS_PREDEFINE_NON_PHYSIC.items():
        enumTup = enumTup + ((key,item['name'],""),)
    return enumTup

def I3DgetPredefineNonPhysicAttr(itemName):
    """ Returns a formatted Tuple of the predefined non Physics Item Attributes """

    return SETTINGS_PREDEFINE_NON_PHYSIC[itemName]['attributeValues']

def I3DAttributeValueIsDefault(m_node,m_attr):
    """ Checks if the m_attr is the default value of m_node"""

    m_val = I3DGetAttributeValue(m_node,m_attr)
    m_default = ""
    if ( m_attr in SETTINGS_ATTRIBUTES):
        m_default = SETTINGS_ATTRIBUTES[m_attr]['defaultValue']
    if ( m_attr in SETTINGS_UI):
        m_default = SETTINGS_UI[m_attr]['defaultValue']
    if (m_default==m_val):
        return True
    else:
        return False

def I3DGetAttributeValue(m_node, m_attr):
    """ Returns value of m_attr of the object m_node, returns default if not set """

    if(dcc.I3DAttributeExists(m_node, m_attr)):
        return dcc.I3DGetAttr(m_node, m_attr)
    else:
        if ( m_attr in SETTINGS_ATTRIBUTES):
            return SETTINGS_ATTRIBUTES[m_attr]['defaultValue']
        if ( m_attr in SETTINGS_UI):
            return SETTINGS_UI[m_attr]['defaultValue']
    return ""

def I3DSaveAttributeBool(m_node, m_attr, m_val):
    if(not dcc.I3DAttributeExists(m_node, m_attr)):
        dcc.I3DAddAttrBool(m_node,m_attr)
    dcc.I3DSetAttrBool(m_node,m_attr,m_val)

def I3DSaveAttributeInt(m_node, m_attr, m_val):
    if(not dcc.I3DAttributeExists(m_node, m_attr)):
        dcc.I3DAddAttrInt(m_node,m_attr)
    dcc.I3DSetAttrInt(m_node,m_attr,m_val)

def I3DSaveAttributeFloat(m_node, m_attr, m_val):
    if(not dcc.I3DAttributeExists(m_node, m_attr)):
        dcc.I3DAddAttrFloat(m_node,m_attr)
    dcc.I3DSetAttrFloat(m_node,m_attr,m_val)

def I3DSaveAttributeString(m_node, m_attr, m_val):
    if(not dcc.I3DAttributeExists(m_node, m_attr)):
        dcc.I3DAddAttrString(m_node,m_attr)
    dcc.I3DSetAttrString(m_node,m_attr,m_val)

def I3DSaveAttributeEnum(node,attr,val):
    if(not dcc.I3DAttributeExists(node, attr)):
        dcc.I3DAddAttrEnum(node,attr)
    dcc.I3DSetAttrEnum(node,attr,val)

def I3DLoadObjectAttributes():
    """ Loads all attributes, loads default if nothing specified """

    m_nodes = dcc.getSelectedNodes()
    if(0 != len(m_nodes)):
        m_node = m_nodes[0]
        for k,v in SETTINGS_ATTRIBUTES.items():
            if   v['type'] == TYPE_BOOL:
                dcc.UISetAttrBool(k,I3DGetAttributeValue(m_node, k))
            elif v['type'] == TYPE_INT:
                dcc.UISetAttrInt(k,I3DGetAttributeValue(m_node, k))
            elif v['type'] == TYPE_FLOAT:
                dcc.UISetAttrFloat(k,I3DGetAttributeValue(m_node, k))
            elif v['type'] == TYPE_STRING:
                dcc.UISetAttrString(k,I3DGetAttributeValue(m_node, k))
            elif v['type'] == TYPE_STRING_UINT:
                dcc.UISetAttrString(k,I3DGetAttributeValue(m_node, k))
            elif v['type'] == TYPE_ENUM:
                dcc.UISetAttrEnum(k,I3DGetAttributeValue(m_node, k))
        dcc.UISetLoadedNode(m_node)
        # Show light attributes only if the selected node is a light
        if dcc.getNodeType(m_node) == "TYPE_LIGHT":
            dcc.UISetAttrBool("UI_showLightAttributes", True)
            dcc.UISetAttrBool("UI_lightUseShadow", dcc.getLightDataFromAPI(m_node, "use_shadow"))
        else:
            dcc.UISetAttrBool("UI_showLightAttributes", False)
    else:
        dcc.UIShowWarning('Nothing selected')

def I3DgetNodeIndex(nodeStr):
    """ Returns the Node Index for the XML configuration"""
    return dcc.getNodeIndex(nodeStr)

def I3DSaveObjectAttributes():
    """ Save the current Settings to the loaded object"""

    m_node = dcc.UIGetLoadedNode()
    if(None is not m_node):
        I3DSaveAttributes(m_node)
    else:
        dcc.UIShowWarning('Nothing loaded')

def I3DRemoveObjectAttributes():
    """ Sets the attributes to the default value """

    m_node = dcc.UIGetLoadedNode()
    if(None is not m_node):
        I3DRemoveAttributes(m_node)
        I3DLoadObjectAttributes()
    else:
        dcc.UIShowWarning('Nothing loaded')

def I3DApplySelectedAttributes():
    """ Save the current Settings to the all selected object"""

    m_nodes = dcc.getSelectedNodes()
    if(0 != len(m_nodes)):
        for m_node in m_nodes:
            I3DSaveAttributes(m_node)
    else:
        dcc.UIShowWarning('Nothing selected')

def I3DRemoveSelectedAttributes():
    """ Deletes all settings from the selected objects and loads defaults"""

    m_nodes = dcc.getSelectedNodes()
    if(0 != len(m_nodes)):
        for m_node in m_nodes:
            I3DRemoveAttributes(m_node)
        I3DLoadObjectAttributes()
    else:
        dcc.UIShowWarning('Nothing selected')

def I3DRemoveAttributes(m_node):
    """ Delete all attributes from SETTINGS_ATTRIBUTES"""

    for k, v in SETTINGS_ATTRIBUTES.items():
        dcc.I3DRemoveAttribute(m_node, k)

def I3DSaveAttributes(m_node):
    """ Saves the current values to the object"""

    for k, v in SETTINGS_ATTRIBUTES.items():
        if   v['type'] == TYPE_BOOL:
            I3DSaveAttributeBool(m_node,   k, UIGetAttrBool(k) )
        elif v['type'] == TYPE_INT:
            I3DSaveAttributeInt(m_node,    k, UIGetAttrInt(k) )
        elif v['type'] == TYPE_FLOAT:
            I3DSaveAttributeFloat(m_node,  k, UIGetAttrFloat(k) )
        elif v['type'] == TYPE_STRING:
            I3DSaveAttributeString(m_node, k, UIGetAttrString(k) )
        elif v['type'] == TYPE_STRING_UINT:
            I3DSaveAttributeString(m_node, k, UIGetAttrString(k) )
        elif v['type'] == TYPE_ENUM:
            I3DSaveAttributeEnum(m_node, k, UIGetAttrEnum(k))
    
    # If the node is a light, update the use_shadow flag
    if dcc.getNodeType(m_node) == "TYPE_LIGHT":
        dcc.setLightData(m_node, "use_shadow", dcc.UIGetAttrBool("UI_lightUseShadow"))

# def I3DApplyMaterialTemplateToSelection():
#     m_nodes = dcc.getSelectedNodes()
#     if(0 != len(m_nodes)):
#         for m_node in m_nodes:
#             I3DRemoveAttributes(m_node)
#         I3DLoadObjectAttributes()
#     else:
#         dcc.UIShowWarning('Nothing selected')

def I3DApplyMaterialTemplateToSelection():
    m_nodes = dcc.getSelectedNodes()
    if(0 != len(m_nodes)):
        for m_node in m_nodes:
            I3DRemoveAttributes(m_node)
        I3DLoadObjectAttributes()
    else:
        dcc.UIShowWarning('Nothing selected')

def I3DApplyMaterialTemplateToSelection():
    m_nodes = dcc.getSelectedNodes()
    if(0 != len(m_nodes)):
        for m_node in m_nodes:
            I3DRemoveAttributes(m_node)
        I3DLoadObjectAttributes()
    else:
        dcc.UIShowWarning('Nothing selected')

def UIGetAttrBool(m_attr):
    """ Get Attribute, if it is not set, return default value """

    if dcc.UIAttrExists(m_attr):
        return dcc.UIGetAttrBool(m_attr)
    else:
        if ( m_attr in SETTINGS_ATTRIBUTES):
            return SETTINGS_ATTRIBUTES[m_attr]['defaultValue']
        if ( m_attr in SETTINGS_UI):
            return SETTINGS_UI[m_attr]['defaultValue']
    return False

def UIGetAttrInt(m_attr):
    """ Get Attribute, if it is not set, return default value """

    if dcc.UIAttrExists(m_attr):
        return dcc.UIGetAttrInt(m_attr)
    else:
        if ( m_attr in SETTINGS_ATTRIBUTES):
            return SETTINGS_ATTRIBUTES[m_attr]['defaultValue']
        if ( m_attr in SETTINGS_UI):
            return SETTINGS_UI[m_attr]['defaultValue']
    return int(0)

def UIGetAttrFloat(m_attr):
    """ Get Attribute, if it is not set, return default value """

    if dcc.UIAttrExists(m_attr):
        return dcc.UIGetAttrFloat(m_attr)
    else:
        if ( m_attr in SETTINGS_ATTRIBUTES):
            return SETTINGS_ATTRIBUTES[m_attr]['defaultValue']
        if ( m_attr in SETTINGS_UI):
            return SETTINGS_UI[m_attr]['defaultValue']
    return float(0.0)

def UIGetAttrString(m_attr):
    """ Get Attribute, if it is not set, return default value """

    if dcc.UIAttrExists(m_attr):
        return dcc.UIGetAttrString(m_attr)
    else:
        if ( m_attr in SETTINGS_ATTRIBUTES):
            return SETTINGS_ATTRIBUTES[m_attr]['defaultValue']
        if ( m_attr in SETTINGS_UI):
            return SETTINGS_UI[m_attr]['defaultValue']
    return str("")

def UIGetAttrEnum(attr):
    """ Get Attribute, if it is not set, return default value """

    if dcc.UIAttrExists(attr):
        return dcc.UIGetAttrEnum(attr)
    else:
        if(attr in SETTINGS_ATTRIBUTES):
            return SETTINGS_ATTRIBUTES[attr]['defaultValue']
        if (attr in SETTINGS_UI):
            return SETTINGS_UI[attr]['defaultValue']
    return str("no enum")

def getBoneData(boneStr,armatureStr):
    """ Initialize all necessary data of the given bone """

    nodeData = {}
    nodeData["name"] = boneStr
    nodeData["type"] = "TYPE_TRANSFORM_GROUP"
    nodeData['armature'] = armatureStr
    isTail = False
    if(boneStr.split("_")[-1] == "tail" ): #check if tail of bone
        isTail = True
        boneStr = boneStr.rsplit("_",1)[0]
    if(isTail):
        nodeData = dcc.getBoneData(boneStr,nodeData['armature'],nodeData)
        nodeData["fullPathName"] = nodeData["fullPathName"] + "_tail"
        nodeData["name"] = nodeData["name"] + "_tail"
        translation = dcc.getBoneTailTranslation( boneStr,nodeData['armature'])
    else:
        nodeData = dcc.getBoneData(boneStr,nodeData['armature'],nodeData)
        translation, rotation, scale = dcc.getBoneTranslationRotationScale(boneStr,nodeData['armature'])
        nodeData["rotation"] = rotation
        nodeData["scale"] = scale
    visibility = True       #bone cannot be hidden
    nodeData["translation"]   = translation
    nodeData["visibility"] = visibility
    return nodeData



def fixUpI3dParamsFromSetting(sgNodes):
    """ Initialize all necessary settings values on the scenegraph nodes this was moved from the constructor of the nodes because 
    it very slow due to how the dcc was having to do multiple lookups to different dictionaries to get attributes. 
    speed tests show a 12X speed improvement here on large test scenes """

    if "blender" == DCC_PLATFORM:
        defaultValues = {}
        attrkeys = SETTINGS_ATTRIBUTES.keys();
        for attr in attrkeys:
            default = ""
            if ( attr in SETTINGS_ATTRIBUTES):
                default = SETTINGS_ATTRIBUTES[attr]['defaultValue']
            if ( attr in SETTINGS_UI):
                default = SETTINGS_UI[attr]['defaultValue']
            defaultValues[attr] = default

    
        for sgnodeId, sgnode in sgNodes.items():
            if sgnodeId in bpy.data.objects:
                node = bpy.data.objects[sgnodeId]
                for attr in attrkeys :
                    if (attr in node):
                        value = node[attr]
                        if value != defaultValues[attr]:
                            sgnode._data[attr] = value
                #backwards compatabilty thing
                if "I3D_boundingVolume" in node and node["I3D_boundingVolume"] == "":
                     sgnode._data["I3D_boundingVolume"] = 'None'


def getNodeData(nodeStr):
    """ Initialize all necessary data of the given node """

    nodeData = {}



    nodeData["fullPathName"] = "ROOT"
    nodeData["name"] = "ROOT"
    nodeData["type"] = "TYPE_TRANSFORM_GROUP"
    """ removing this code as setting up of these attributes is done in the function fixUpI3dParamsFromSetting later on in the export process"""
    #for key in SETTINGS_ATTRIBUTES.keys():
    #    if (not I3DAttributeValueIsDefault(nodeStr,key)):        #log all non default values
    #        nodeData[key] = I3DGetAttributeValue(nodeStr,key)
    if ("ROOT" == nodeStr):
        return nodeData
    nodeData = dcc.getNodeData(nodeStr,nodeData)
    m_translation, m_rotation, m_scale = dcc.getNodeTranslationRotationScale( nodeStr )
    m_visibility = dcc.isNodeVisible(nodeStr)
    nodeObj = bpy.data.objects[nodeStr]
    if nodeObj and "I3D_forceVisibleFlag" in nodeObj :
        m_visibility = nodeObj["I3D_forceVisibleFlag"]

    nodeData["translation"]   = m_translation
    nodeData["rotation"]      = m_rotation
    nodeData["scale"]         = m_scale
    nodeData["visibility"]    = m_visibility
    if ("TYPE_LIGHT"== nodeData["type"]):
        nodeData["lightData"]  = getLightData(nodeStr)
    if ("TYPE_CAMERA"== nodeData["type"]):
        nodeData["cameraData"] = getCameraData(nodeStr)
    return nodeData

def getMaterialData(m_node):
    """ Initialize necessary material data """

    m_nodeData = {}
    m_nodeData["fullPathName"] = m_node
    m_nodeData["name"] = "default"
    m_nodeData["diffuseColor"]  = "0.5 0.5 0.5 1"
    m_nodeData["specularColor"] = "0 1 0"
    return dcc.getMaterialData(m_node,m_nodeData)

def isReallyasolute(path):
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

def getFileData(pathStr,fileType):
    """ Initialize necessary file data """

    nodeData = {}
    nodeData["fullPathName"] = pathStr
    nodeData["relativePath"] = "false"
    if fileType in ["Texture","Glossmap","Normalmap","Emissivemap"]:
        nodeData = dcc.getFileData(pathStr,nodeData)

    elif fileType == "customShader" or fileType.startswith("customTexture") or fileType.startswith("customBuffer"):
        nodeData = dcc.getFileData(pathStr,nodeData)
    else:
        nodeData["filename"] = pathStr
        if isReallyasolute(pathStr):
            nodeData["relativePath"] = "true"
    return nodeData

def getInstances(m_node):
    m_nodes = dcc.getNodeInstances(m_node)
    return m_nodes

def getShapeData(m_shape,m_sceneNodeData):
    """
    Initialize necessary shape data

    :param m_shape: the name of the shape node object
    :param m_sceneNodeData: the structure to complete
    """

    m_type = m_sceneNodeData['type']
    m_nodeData = {}
    m_nodeData["name"]        = "Undefined"
    if ( "TYPE_MESH" == m_type ):
        m_nodeData["isOptimized"] = "false"
        m_nodeData = dcc.getShapeData(m_shape,m_nodeData,m_sceneNodeData)
    elif("TYPE_NURBS_CURVE" == m_type):
        m_nodeData["name"]   = "Undefined"
        m_nodeData["degree"] = "3"
        m_nodeData["form"]   = "open"
        m_nodeData = dcc.getNurbsCurveData(m_shape,m_nodeData)
    return m_nodeData

def getLightData(m_node):
    """ Initialize necessary light data """

    m_light = {}
    m_light["type"]             = "directional"
    m_light["color"]            = "1 1 1"
    m_light["emitDiffuse"]      = "true"
    m_light["emitSpecular"]     = "true"
    m_light["range"]            = "100"
    m_light["castShadowMap"]    = "true"
    return  dcc.getLightData(m_node, m_light)

def getCameraData(m_node):
    """ Initialize necessary camera data """

    m_camera = {}
    m_camera["fov"]      = "60"
    m_camera["nearClip"] = "0.1"
    m_camera["farClip"]  = "10000"
    return dcc.getCameraData(m_node, m_camera)
