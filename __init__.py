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

bl_info = {
    "name": "Project Motor Racing I3D Exporter Tools",
    "author": "GIANTS Software & Straight4 Studios",
    "blender": ( 3, 6, 21 ),
    "version": ( 10, 5, 00 ),
    "location": "PMR GIANTS I3D",
    "description": "GIANTS Utilities and Exporter for Project Motor Racing",
    "warning": "",
    "wiki_url": "http://gdn.giants-software.com",
    "tracker_url": "http://gdn.giants-software.com",
    "category": "Game Engine"}

global DCC_PLATFORM
DCC_PLATFORM = "blender"

if "bpy" in locals():
    import importlib
    importlib.reload(i3d_ui)
    importlib.reload(dcc)
    importlib.reload(i3d_export)
else:
    from . import i3d_ui
    from . import dcc
    from . import i3d_export
import bpy


class I3D_MT_Menu( bpy.types.Menu ):
    """  GUI element in bottom left corner to open the PMR GIANTS I3D Exporter """

    bl_label = "PMR GIANTS I3D"
    bl_idname = "I3D_MT_Menu"

    def draw( self, context ):
        """pop up menu when clicked"""

        layout = self.layout
        layout.label( text = "v {0}".format(bl_info["version"]) )
        layout.operator( "i3d.menuexport" )

def draw_I3D_Menu( self, context ):
    """ Draw I3D Menu """

    self.layout.menu( I3D_MT_Menu.bl_idname )

#-------------------------------------------------------------------------------
#   Register
#-------------------------------------------------------------------------------
def register():
    i3d_ui.register()
    bpy.utils.register_class( I3D_MT_Menu )
    bpy.types.STATUSBAR_HT_header.prepend(draw_I3D_Menu)


def unregister():
    bpy.types.STATUSBAR_HT_header.remove(draw_I3D_Menu)
    bpy.utils.unregister_class( I3D_MT_Menu )
    i3d_ui.unregister()


if __name__ == "__main__":
    register()