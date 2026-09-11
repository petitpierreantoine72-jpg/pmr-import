import bpy
import bmesh
from mathutils import Vector


def meshchop_is_all_triangles(mesh):
    """Check if all faces in the mesh are triangles."""
    for face in mesh.polygons:
        if len(face.vertices) != 3:
            return False
    return True

def meshchop_triangulate_mesh(mesh):
    if not meshchop_is_all_triangles(mesh):
        # Create a bmesh from the mesh data
        bm = bmesh.new()
        bm.from_mesh(mesh)

        # Triangulate the bmesh
        bmesh.ops.triangulate(bm, faces=bm.faces[:])

        # Write the bmesh back to the mesh data
        bm.to_mesh(mesh)
        bm.free()


def create_deep_copy_object(original_obj):
    """Create a deep copy of a Blender object, including custom properties."""
    obj_copy = original_obj.copy()
    obj_copy.data = original_obj.data.copy()
    
    # Copy custom properties
    for prop in original_obj.keys():
        if prop not in {'_RNA_UI'}:
            obj_copy[prop] = original_obj[prop]
    
    return obj_copy

def get_local_aabb(obj):
    """Get the Axis-Aligned Bounding Box of the object in local coordinates."""
    local_bbox_corners = [Vector(corner) for corner in obj.bound_box]
    min_corner = Vector((min(corner.x for corner in local_bbox_corners),
                         min(corner.y for corner in local_bbox_corners),
                         min(corner.z for corner in local_bbox_corners)))
    max_corner = Vector((max(corner.x for corner in local_bbox_corners),
                         max(corner.y for corner in local_bbox_corners),
                         max(corner.z for corner in local_bbox_corners)))
    return min_corner, max_corner

def get_equal_grid_positions(min_corner, max_corner, max_size_x, max_size_y, max_size_z):
    """Get grid positions with equal sizes based on max size."""
    def create_positions(min_val, max_val, max_size):
        if max_size == 0:
            return [min_val, max_val]
        length = max_val - min_val
        num_cells = int(length / max_size) + (1 if length % max_size > 0 else 0)  # Calculate the number of cells
        cell_size = length / num_cells  # Adjust cell size to fit evenly
        positions = [min_val + i * cell_size for i in range(num_cells)]
        positions.append(max_val)  # Ensure the last position is the max_val
        return positions

    x_positions = create_positions(min_corner.x, max_corner.x, max_size_x)
    y_positions = create_positions(min_corner.y, max_corner.y, max_size_y)
    z_positions = create_positions(min_corner.z, max_corner.z, max_size_z)
    
    return x_positions, y_positions, z_positions

def create_aabb_list(min_corner, max_corner, max_size_x, max_size_y, max_size_z):
    """Create a list of AABB items for each grid cell."""
    x_positions, y_positions, z_positions = get_equal_grid_positions(min_corner, max_corner, max_size_x, max_size_y, max_size_z)
    aabb_list = []
    
    for i in range(len(x_positions) - 1):
        for j in range(len(y_positions) - 1):
            for k in range(len(z_positions) - 1):
                aabb_min = Vector((x_positions[i], y_positions[j], z_positions[k]))
                aabb_max = Vector((x_positions[i + 1], y_positions[j + 1], z_positions[k + 1]))
                aabb_list.append((aabb_min, aabb_max))
    
    return aabb_list

def normalize_uvs(obj, uv_range_min=-32, uv_range_max=32):
    """Normalize the UV coordinates of a mesh to be within the specified range, shifting by whole numbers."""
    if obj.type != 'MESH':
        print(f"Object {obj.name} is not a mesh. Skipping UV normalization.")
        return
    
    mesh = obj.data
    
    for uv_layer in mesh.uv_layers:
        uv_min = Vector((float('inf'), float('inf')))
        uv_max = Vector((float('-inf'), float('-inf')))

        # Find the min and max UV coordinates for the current UV layer
        for loop in mesh.loops:
            uv = uv_layer.data[loop.index].uv
            uv_min.x = min(uv_min.x, uv.x)
            uv_min.y = min(uv_min.y, uv.y)
            uv_max.x = max(uv_max.x, uv.x)
            uv_max.y = max(uv_max.y, uv.y)

        # Initialize UV shifts
        uv_shift_x = 0
        uv_shift_y = 0

        # Calculate the range of UV coordinates
        uv_range_x = uv_max.x - uv_min.x
        uv_range_y = uv_max.y - uv_min.y

        # Check if the UV range exceeds the specified limits
        if uv_range_x > (uv_range_max - uv_range_min) or uv_range_y > (uv_range_max - uv_range_min):
            print("Skipping normalization for UV layer due to UV range exceeding specified limits.")
            continue

        # Calculate the shift needed to bring UVs within the specified range
        if uv_min.x < uv_range_min and uv_max.x > uv_range_max:
            print("Skipping normalization for UV layer due to UV range exceeding specified limits.")
            continue
        elif uv_min.x < uv_range_min:
            uv_shift_x = uv_range_min - uv_min.x
        elif uv_max.x > uv_range_max:
            uv_shift_x = uv_range_max - uv_max.x

        # Ensure we shift by whole numbers
        uv_shift_x = int(uv_shift_x)

        if uv_min.y < uv_range_min and uv_max.y > uv_range_max:
            print("Skipping normalization for UV layer due to UV range exceeding specified limits.")
            continue
        elif uv_min.y < uv_range_min:
            uv_shift_y = uv_range_min - uv_min.y
        elif uv_max.y > uv_range_max:
            uv_shift_y = uv_range_max - uv_max.y

        # Ensure we shift by whole numbers
        uv_shift_y = int(uv_shift_y)

        # Apply the shift to all UV coordinates in the current UV layer
        if uv_shift_x != 0 or uv_shift_y != 0:
            for loop in mesh.loops:
                uv = uv_layer.data[loop.index].uv
                uv_layer.data[loop.index].uv = Vector((uv.x + uv_shift_x, uv.y + uv_shift_y))

def link_object_to_same_collection_as(target_obj, new_obj):
    # Function to find the collection containing the target object
    def find_collection_recursive(obj, collection):
        # Check if the object is in the current collection
        if obj.name in collection.objects:
            return collection
        # Recursively check subcollections
        for subcollection in collection.children:
            found_collection = find_collection_recursive(obj, subcollection)
            if found_collection:
                return found_collection
        return None

    # If the target object has a parent, the parent may belong to a different collection.
    # We need to find the highest parent and link to the collection that contains it.
    highest_parent = target_obj
    while highest_parent.parent:
        highest_parent = highest_parent.parent

    # Start the search from the top-level collections to find the appropriate collection
    found_collection = None
    for collection in bpy.data.collections:
        found_collection = find_collection_recursive(highest_parent, collection)
        if found_collection:
            break

    # Link the new object to the found collection, or to the active collection as a fallback
    if found_collection:
        found_collection.objects.link(new_obj)
        print(f"Object '{new_obj.name}' linked to collection '{found_collection.name}'")
    else:
        # Fallback: link the object to the current active collection
        bpy.context.collection.objects.link(new_obj)
        print(f"Object '{new_obj.name}' linked to the active collection as a fallback")

    # Set the new object's parent to the target object's parent if it exists
    if target_obj.parent:
        new_obj.parent = target_obj.parent

    # Update the view layer to ensure the changes are visible
    bpy.context.view_layer.update()


def create_new_mesh(original_obj, nameappend , data_transferwanted ):
    """Create a new mesh and object from the original object."""
    # Deep copy the original object to retain all properties, including materials and UV maps
    new_mesh_data = original_obj.data.copy()
    new_obj = bpy.data.objects.new(f"{original_obj.name}_{nameappend}", new_mesh_data)

    # Link the new object
    link_object_to_same_collection_as(original_obj, new_obj)


    # Set the new object's location to match the original object's location
    new_obj.location = original_obj.location

    # Enable Auto Smooth to allow custom normals
    new_obj.data.use_auto_smooth = True
    new_obj.data.auto_smooth_angle = 3.14159  # Set an appropriate angle for auto smooth (45 degrees)

    if data_transferwanted :
        # Data Transfer Modifier to transfer normals
        data_transfer_mod = new_obj.modifiers.new(name="DataTransfer", type='DATA_TRANSFER')
        data_transfer_mod.object = original_obj
        data_transfer_mod.use_loop_data = True
        data_transfer_mod.data_types_loops = {'CUSTOM_NORMAL'}
        data_transfer_mod.loop_mapping = 'POLYINTERP_NEAREST'
        data_transfer_mod.mix_mode = 'REPLACE'
        data_transfer_mod.use_max_distance = True
        data_transfer_mod.max_distance = 0.01  # Adjust as needed

    meshchop_triangulate_mesh(new_obj.data)
    # Update the new object's data to ensure normals are correctly applied
    new_obj.data.update()

    return new_obj



def chop_mesh_with_aabb(new_obj, aabb_min, aabb_max):
    """Bisect the given mesh based on the provided AABB dimensions."""
    new_mesh = new_obj.data

    # Create a new bmesh from the mesh
    bm = bmesh.new()
    bm.from_mesh(new_mesh)

    # Define planes with adjustments for precision alignment
    planes = [
        (Vector((aabb_min.x, 0, 0)), Vector((1, 0, 0))),
        (Vector((aabb_max.x, 0, 0)), Vector((-1, 0, 0))),
        (Vector((0, aabb_min.y, 0)), Vector((0, 1, 0))),
        (Vector((0, aabb_max.y, 0)), Vector((0, -1, 0))),
        (Vector((0, 0, aabb_min.z)), Vector((0, 0, 1))),
        (Vector((0, 0, aabb_max.z)), Vector((0, 0, -1)))
    ]

    for plane_co, plane_no in planes:
        bmesh.ops.bisect_plane(
            bm,
            geom=bm.faces[:] + bm.edges[:] + bm.verts[:],
            dist=0,
            plane_co=plane_co,
            plane_no=plane_no,
            use_snap_center=False,
            clear_outer=False,
            clear_inner=False
        )

    # Ensure to clean up only those vertices that have become isolated due to bisecting
    isolated_verts = [v for v in bm.verts if len(v.link_faces) == 0]
    bmesh.ops.delete(bm, geom=isolated_verts, context='VERTS')

    # Merge duplicate vertices created during bisect operation
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)

    # Update the new mesh with the modified bmesh
    bm.to_mesh(new_mesh)
    bm.free()

    meshchop_triangulate_mesh(new_obj.data)

    return new_obj



def create_new_mesh_from_aabb(original_obj, aabb_min, aabb_max, original_name, index):
    """Create a new mesh and object from the AABB."""
    # Deep copy the original object to retain all properties, including materials and UV maps
    new_obj = create_deep_copy_object(original_obj)
    new_mesh = new_obj.data

    # Set the new object's name and the new mesh's name
    new_name = f"{original_name}_part_{index}"
    new_obj.name = new_name
    new_mesh.name = new_name

    # Create a new bmesh
    bm = bmesh.new()
    bm.from_mesh(new_mesh)
    # Define a tolerance value to handle floating-point precision issues
    tolerance = 0.0000001

    # Define planes with adjustments for precision alignment
    planes = [
        (Vector((aabb_min.x , 0, 0)), Vector((1, 0, 0))),
        (Vector((aabb_max.x , 0, 0)), Vector((-1, 0, 0))),
        (Vector((0, aabb_min.y , 0)), Vector((0, 1, 0))),
        (Vector((0, aabb_max.y , 0)), Vector((0, -1, 0))),
        (Vector((0, 0, aabb_min.z )), Vector((0, 0, 1))),
        (Vector((0, 0, aabb_max.z )), Vector((0, 0, -1)))
    ]

    # Remove geometry outside the AABB
    verts_to_delete = [v for v in bm.verts if not (aabb_min.x-tolerance <= v.co.x <= aabb_max.x+tolerance and 
                                                   aabb_min.y-tolerance <= v.co.y <= aabb_max.y+tolerance and 
                                                   aabb_min.z-tolerance <= v.co.z <= aabb_max.z+tolerance)]
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')

    # Ensure that we remove isolated vertices that have no edges or faces
    isolated_verts = [v for v in bm.verts if len(v.link_edges) == 0 and len(v.link_faces) == 0]
    bmesh.ops.delete(bm, geom=isolated_verts, context='VERTS')

    # Create the new mesh and object
    if len(bm.verts) == 0:
        bm.free()
        if (new_obj.data):
            bpy.data.meshes.remove(new_obj.data)

        # Remove the associated mesh from Blender data
        try:
            if new_obj:
                bpy.data.objects.remove(new_obj, do_unlink=True)
        except:
            pass 

        return None

    new_center = (aabb_min + aabb_max) / 2

   
    # Adjust vertices to be relative to the new center
    for v in bm.verts:
        v.co -= new_center
    bm.to_mesh(new_mesh)
    bm.free()

            
    # Link the new object
    link_object_to_same_collection_as(original_obj, new_obj)

    # Adjust the local matrix to place the object correctly
    new_obj.location = original_obj.location + new_center

    # Force update to ensure matrix_local reflects the changes
    bpy.context.view_layer.update()
    # Normalize UV coordinates
    normalize_uvs(new_obj)

    meshchop_triangulate_mesh(new_obj.data)


    return new_obj


def chop_mesh_by_size(original_obj, max_size_x, max_size_y, max_size_z, customattributeName=""):
    """Chop the mesh into smaller parts based on the maximum dimension size."""
    # Get AABB in local coordinates
    min_corner, max_corner = get_local_aabb(original_obj)
    
    print(f"OK: Chopping mesh with max size {max_size_x} {max_size_y} {max_size_z}")
    print(f"Local BBox Min: {min_corner}, Max: {max_corner}")

    # Check if the mesh needs to be chopped
    if (max_corner.x - min_corner.x <= max_size_x) and (max_corner.y - min_corner.y <= max_size_y) and (max_corner.z - min_corner.z <= max_size_z):
        return []

    # Create AABB list
    aabb_list = create_aabb_list(min_corner, max_corner, max_size_x, max_size_y, max_size_z)
    
    if len(aabb_list) <= 1 :
    	return [] 
    
    for aabb_min, aabb_max in aabb_list:
        print(f"Created AABB: Min: {aabb_min}, Max: {aabb_max}")
    
    new_objects = []
    index = 0  # Index counter for naming

    base_obj = original_obj
    base_tands = None
    if meshchop_is_all_triangles(original_obj.data) == False or original_obj.data.use_auto_smooth != True:
        base_obj = create_new_mesh(original_obj, "tands", False)
        meshchop_triangulate_mesh(base_obj.data);
        base_obj.data.use_auto_smooth = True
        base_obj.data.auto_smooth_angle = 3.14159  # 
        # Recalculate split normals to ensure they are applied properly
        base_obj.data.calc_normals_split()

        # Update the new object's data
        base_obj.data.update()
        base_tands = base_obj;


    new_obj_chopped = create_new_mesh(base_obj, "chopped", True)
    if new_obj_chopped:
            
        # Add custom property to mark the new objects
        if customattributeName != "":
            new_obj_chopped[customattributeName] = True
            new_objects.append(new_obj_chopped)
    
    for aabb_min, aabb_max in aabb_list:
        print(f"Chopping Mesh AABB: Min: {aabb_min}, Max: {aabb_max}")
        chop_mesh_with_aabb(new_obj_chopped, aabb_min, aabb_max);
 
    for aabb_min, aabb_max in aabb_list:
        print(f"Creating Sub Mesh AABB: Min: {aabb_min}, Max: {aabb_max}")
        new_obj = create_new_mesh_from_aabb(new_obj_chopped, aabb_min, aabb_max, original_obj.name, index)
        
        if new_obj:
            # Add custom property to mark the new objects
            if customattributeName != "":
                new_obj[customattributeName] = True
            


            new_objects.append(new_obj)
            index += 1  # Increment index only for valid objects
    
    if customattributeName != "":
         if new_obj_chopped:
             new_obj_chopped["donotexport"] = True
         if base_tands:
             base_tands["donotexport"] = True
   

    return new_objects

def process_exportlist(object_names, max_size_x, max_size_y, max_size_z):
    """Process the list of objects for export and chop them if needed."""
    new_object_list = []
    complete_object_list = []
    for name in object_names:
        obj = bpy.data.objects.get(name)
        if obj and obj.type == 'MESH':
            chopped_objects = chop_mesh_by_size(obj, max_size_x, max_size_y, max_size_z, "unlinkafterExport")
            if len(chopped_objects) > 0:
                new_object_list.extend([new_obj.name for new_obj in chopped_objects])
                for new_obj in chopped_objects:
                    if "donotexport" not in new_obj:
                        complete_object_list.append(new_obj.name)
            else:
                complete_object_list.append(name)
        else:
            complete_object_list.append(name)
    
    return complete_object_list, new_object_list

def cleanupAfterExport(object_names):
    """Clean up the list after export."""
    for name in object_names:
        obj = bpy.data.objects.get(name)
        if obj and obj.type == 'MESH' and "unlinkafterExport" in obj:
            if (obj.data):
                bpy.data.meshes.remove(obj.data)

            # Remove the associated mesh from Blender data
            elif obj :
                bpy.data.objects.remove(obj, do_unlink=True)
