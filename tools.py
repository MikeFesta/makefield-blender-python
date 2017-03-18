# -*- coding: utf-8 -*-
"""
This module contains blender shortcut tools to simplify the code

"""
import bpy, bmesh, math, os
from mathutils import *

def get_context_override_view3d():
    '''The context override needs to be passed for opperations that require a 3D viewport
    This assumes that there is a 3D viewpoint in the default layout
    :returns: A 3D viewport context
    '''
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            break

    for region in area.regions:
        if region.type == 'WINDOW':
            break

    context_override_view3d = bpy.context.copy()
    context_override_view3d['area'] = area
    context_override_view3d['region'] = region
    context_override_view3d['space_data'] = area.spaces[0]
    return context_override_view3d

def get_bmesh_for_object(o):
    '''Create a bmesh and load it with the object's mesh data
    :object o: The bpy.object that contains the mesh
    :returns bmesh: The new bmesh
    '''
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table() # This needs to be run or an error is thrown
    bm.edges.ensure_lookup_table()
    return bm

def update_object_from_bmesh(o, bm):
    '''Updates the mesh data based on the bmesh
    ':object o: The bpy.object to update
    ':bmesh bm: The bmesh with the new data
    '''
    # Ensure we are in object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    bm.to_mesh(o.data)
    select_object(o)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles()
    bpy.ops.object.mode_set(mode='OBJECT')

def collapse_edges_in_order(o, angle):
    '''Loop through all vertices, find their neighbors, collapse if < angle
    :object o: The object with the vertices to collapse
    :float angle: The angle to collapse if less than
    '''
    bm = get_bmesh_for_object(o)

    for v in bm.verts:
        neighbors = get_vertex_neighbors(bm, v.index)
        if (len(neighbors) == 2):
            collapse_points_on_line(
                bm.verts[neighbors[0]],
                v,
                bm.verts[neighbors[1]],
                angle)
        else:
            print('The length of the neighbors was ' + str(len(neighbors)))

    update_object_from_bmesh(o, bm)

def get_vertex_neighbors(bm, v0):
    '''Find the two vertices that are connected
    This assumes that we are dealing with vertices on a line that has two neighbors
    :bmesh bm: The bmesh that the vertex belongs to
    :int v0: The vertex in the middle
    :returns array: The connected vertices
    '''
    edges = []
    for e in bm.edges:
      if (e.verts[0].index == v0):
          edges.append(e.verts[1].index)
      elif (e.verts[1].index == v0):
          edges.append(e.verts[0].index)
    print(edges)
    return edges

def make_matrix(v1, v2, v3):
    '''http://blender.stackexchange.com/questions/30808/how-do-i-construct-a-transformation-matrix-from-3-vertices'''
    a = v2-v1
    b = v3-v1

    c = a.cross(b)
    if c.magnitude>0:
        c = c.normalized()
    else:
        raise BaseException("A B C are colinear")

    b2 = c.cross(a).normalized()
    a2 = a.normalized()
    m = Matrix([a2, b2, c]).transposed()
    s = a.magnitude
    m = Matrix.Translation(v1) * Matrix.Scale(s,4) * m.to_4x4()

    return m


# Not sure why these two lines were here...I was probably testing something
#obj = bpy.context.active_object
#obj.matrix_world = make_matrix(Vector([1,1,1]), Vector([1,2.5,1]), Vector([0.5,1,1.5]) )


def get_planar_angle(v0, v1, v2):
    '''Find the angle of v1 between v0 and v2 
    This is used for planar decimation on a 2d line
    :vertex v0: The first vertex
    :vertex v1: The middle vertex, which is the angle being measured
    :vertex v2: The last vertex
    :returns float: the degree in radians
    '''
    # TODO: Apply a rotation so that the 3 points are on a plane, with v1 located at 0,0

# cos(A) = (b*b + c*c - a*a) / 2*b*c
    a = get_distance_between_points(v0, v2)
    b = get_distance_between_points(v0, v1)
    c = get_distance_between_points(v1, v2)

    if (b == 0 or c == 0):
        return 0
    cos_a = (b*b + c*c - a*a) / (2*b*c)
    return math.acos(cos_a)

def get_distance_between_points(v0, v1):
    '''Find the distance between to points
    :vertex v0: The first vertex
    :vertex v1: The second vertex
    :returns float: The computed distance
    '''
    return math.sqrt(
        math.pow((v0.co.x - v1.co.x), 2) +
        math.pow((v0.co.y - v1.co.y), 2) +
        math.pow((v0.co.z - v1.co.z), 2))

def collapse_points_on_line(v0, v1, v2, angle):
    a = get_planar_angle(v0, v1, v2)
    print(math.degrees(a))
    if (math.degrees(a) > angle):
        print('collapse')
        v1.co = v0.co
        # I shoud be using bmesh in order to get these changes to update

def center_model_by_center_of_mass(model):
    select_object(model)
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
    model.location = (0, 0, model.location.z)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

def delete_all():
    '''Delete all objects in the scene'''
    bpy.ops.object.select_all(action='SELECT')
    delete_selected_objects()

def delete_all_cameras():
    '''Delete all cameras in the scene'''
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.data.objects:
        if (o.type == 'CAMERA'):
            o.select = True
    delete_selected_objects()

def delete_object(obj):
    '''Delete a single object'''
    select_object(obj)
    delete_selected_objects()

def delete_selected_objects():
    '''Delete the selected object'''
    bpy.ops.object.delete()

def export_fbx(obj, name):
    bpy.ops.export_scene.fbx(use_selection=True, filepath=name+'.fbx')

def import_agisoft_scan(fbx_filepath):
    '''Imports an fbx file that came from Agisoft, which may have cameras and should have one object named Model
    :string fbx_filepath: The fbx location to open
    :returns object: The model
    '''
    import_fbx(fbx_filepath)
    delete_all_cameras()

    # There should only be one object remaining
    if(len(bpy.data.objects) != 1):
        raise ValueError('Error: There should be only one object imported - check the contents of the fbx file')
    return bpy.data.objects[0]

def import_fbx(fbx_filepath):
    ''' Import an fbx file at the given path
    :string fbx_filepath: The location of the file to load 
    '''
    bpy.ops.import_scene.fbx(filepath=fbx_filepath)

def move_object_to_layer(obj, layer):
    '''Moves the given object to a given layer
    :object obj: The object to move
    :int layer: The layer number, as numbered in the blender editor (e.i. 1=0, 2=1, ... 0=9)
    '''
    i = layer - 1
    if (layer == 0):
        i = 9
    obj.layers[i] = True 
    for index in range(0, len(obj.layers)):
        if (index != i):
            obj.layers[index] = False

def select_object(obj):
    ''' Select a single object
    :object obj: The object to select
    '''
    if obj is None:
        raise ValueError('Error: the object that you are trying to select does not exist')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.scene.objects.active = obj
    bpy.ops.object.mode_set(mode = 'OBJECT')
    obj.select = True
    bpy.context.scene.objects.active = bpy.context.scene.objects.active # Refresh Selection

def quit_blender():
    bpy.ops.wm.quit_blender()


# Code for creating cubemaps
# This code takes all cameras in the scene and renders out cubemaps for them
# The goal is to make those cube maps available in unity for teleportation or reflection probes
# Bugs:
# - Need to have cyles render selected
# - Need to be in object mode
# - Could not save image to destination (mac and new/unsaved file)

def test():
  '''Shorthand for testing'''
  render_360_images_for_all_cameras()

def render_360_images_for_all_cameras():
    cameras = []
    for o in bpy.data.objects:
        if (o.type == 'CAMERA'):
            cameras.append(o)
    render_360_images_for_cameras(cameras)

def render_360_images_for_cameras(cameras):
    # Get filepath and directory info for saving images and fbx
    directory = os.path.dirname(bpy.data.filepath)

    # Put the cameras into a group for fbx export and cleanup later
    group = bpy.data.groups.new(name='360_cameras')

    for cam in cameras:
        render_360_for_camera(cam, group) # TODO: add a size parameter instead of hard coding 4k

    # Export all objects in the group 360_cameras as an fbx
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_grouped(type='GROUP') #same group as the last active object
    bpy.ops.export_scene.fbx(filepath=directory+'360_cameras.fbx', use_selection=True)

    # Delete the geometry and images used to create the renders
    #cleanup_360_cameras() # TODO: re-enable after testing

def render_360_for_camera(c, g):
    bpy.ops.mesh.primitive_cube_add()
    o = bpy.context.active_object
    g.objects.link(o)
    bpy.ops.object.shade_smooth()
    o.location = c.location
    o.name = c.name.replace('.', '_') + '_360'
    s = o.modifiers.new(name='4xSubSurf', type='SUBSURF')
    s.render_levels = 4
    s.levels = 4 # TODO: Make sure this is a sphere and not cube with rounded corners

    # UV unwrap the sphere and set the correct x,y coords for each face
    m = o.data
    u = m.uv_textures.new()

    x_pos = 0.0
    # +X (8, 11, 9, 10)
    m.uv_layers.active.data[8].uv = (x_pos, 0.0)
    m.uv_layers.active.data[11].uv = (x_pos, 1.0)
    x_pos += 1/6;
    m.uv_layers.active.data[9].uv = (x_pos, 0.0)
    m.uv_layers.active.data[10].uv = (x_pos, 1.0)

    # -X (0, 3, 1, 2) 
    m.uv_layers.active.data[0].uv = (x_pos, 0.0)
    m.uv_layers.active.data[3].uv = (x_pos, 1.0)
    x_pos += 1/6;
    m.uv_layers.active.data[1].uv = (x_pos, 0.0)
    m.uv_layers.active.data[2].uv = (x_pos, 1.0)

    # +Y (4, 7, 5, 6)
    m.uv_layers.active.data[4].uv = (x_pos, 0.0)
    m.uv_layers.active.data[7].uv = (x_pos, 1.0)
    x_pos += 1/6;
    m.uv_layers.active.data[5].uv = (x_pos, 0.0)
    m.uv_layers.active.data[6].uv = (x_pos, 1.0)

    # -Y (12, 15, 13, 14)
    m.uv_layers.active.data[12].uv = (x_pos, 0.0)
    m.uv_layers.active.data[15].uv = (x_pos, 1.0)
    x_pos += 1/6;
    m.uv_layers.active.data[13].uv = (x_pos, 0.0)
    m.uv_layers.active.data[14].uv = (x_pos, 1.0)

    # +Z (20, 23, 21, 22)
    m.uv_layers.active.data[20].uv = (x_pos, 0.0)
    m.uv_layers.active.data[23].uv = (x_pos, 1.0)
    x_pos += 1/6;
    m.uv_layers.active.data[21].uv = (x_pos, 0.0)
    m.uv_layers.active.data[22].uv = (x_pos, 1.0)

    # -Z (16, 19, 17, 18)
    m.uv_layers.active.data[16].uv = (x_pos, 0.0)
    m.uv_layers.active.data[19].uv = (x_pos, 1.0)
    x_pos += 1/6;
    m.uv_layers.active.data[17].uv = (x_pos, 0.0)
    m.uv_layers.active.data[18].uv = (x_pos, 1.0)

    # Create a new image (bake target)
    img = bpy.data.images.new(name=o.name, width=4096, height=2048)
    img.filepath_raw = '//' + o.name + '.png'

    # Create a new material
    mat = bpy.data.materials.new(name=o.name)
    mat.use_nodes = True
    out_node = mat.node_tree.nodes['Material Output']
    bsdf_node = mat.node_tree.nodes['Diffuse BSDF']
    # TODO: not sure how to delete this node - probably not important
    gloss_node = mat.node_tree.nodes.new(type='ShaderNodeBsdfGlossy')
    gloss_node.inputs[1].default_value = 0
    mat.node_tree.links.new(gloss_node.outputs[0], out_node.inputs[0])
    img_tex = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
    img_tex.image = img

    # Link the material to the cube
    m.materials.append(mat)

    # Render and save image to file
    bpy.ops.object.bake(type='COMBINED')
    img.save()

def cleanup_360_cameras():
    '''Remove the objects, materials, and images created'''
    # This is making the assumption that it is called with all of the cubes selected
    bpy.ops.object.delete()
    for i in bpy.data.images:
        if (i.name.find('Camera') == 0):
            i.user_clear()

    for m in bpy.data.materials:
        if (m.name.find('Camera') == 0):
            m.user_clear()
    # I may not need to remove them from the group because they have been deleted and the group is gone
    #bpy.ops.group.objects_remove_all(bpy.data.groups['360_cameras'])
