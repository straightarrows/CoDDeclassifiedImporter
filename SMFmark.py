bl_info = {
    "name": "Import SMF models",
    "author": "Mark",
    "version": (0,1),
    "blender": (2, 93, 1),
    "location": "File > Export > Omikron model (*.smf)",
    "description": 'Import models from "Call of Duty Declassified"',
    "warning": "",
    "wiki_url": "",
    "category": "Import-Export"
}

import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from mathutils import *
import re #regex
import time
import os # for path stuff
import ntpath
import math 

from bpy.props import CollectionProperty #for multiple files
from bpy.types import OperatorFileListElement

try:
    import struct
except:
    struct = None

def ReadInt32(fileobject):
    intstr = fileobject.read(4)
    return struct.unpack('<i',intstr)[0]

def ReadFloat(fileobject):
    floatstr = fileobject.read(4)
    return struct.unpack('<f', floatstr)[0]

def ReadShort(fileobject):
    Shortstr = fileobject.read(2)
    return struct.unpack('<H', Shortstr)[0]
    
def ReadShortTriple(fileobject):
    a = ReadShort(fileobject)
    b = ReadShort(fileobject)
    c = ReadShort(fileobject)
    
    return [a,b,c]

def ReadVector(fileobject):
    x = ReadFloat(fileobject)
    y = ReadFloat(fileobject)
    z = ReadFloat(fileobject)
    #print (x)
    #print(y)
    #print(z)
    return Vector([x,y,z])

def ReadFaceIndex(fileobject):
    fileobject.seek(14604,0) 
    faceindexlist = []
    for i in range(306): #this is not supposed to be same as floats
        faceindextriple = ReadShortTriple(fileobject)
        #print(faceindextriple)
        faceindexlist.append(faceindextriple)
        #fileobject.seek(1,1)
    return faceindexlist
    

def ImportModel(fileobject, offsettomodel, modelcomplex):
    fileobject.seek(offsettomodel,0) 
    vertexlist = [] 
    if modelcomplex:
        seekvalue = 32
    else:
        seekvalue = 28
    for i in range(180): 
        vertex = ReadVector(fileobject)
        vertexlist.append(vertex)
        fileobject.seek(seekvalue,1)
    print(vertexlist)
    faceindexlist = ReadFaceIndex(fileobject)
    print(faceindexlist)
    
    mesh = bpy.data.meshes.new("Cod_Vita_Mesh")
    mesh.from_pydata(vertexlist,[],faceindexlist)
    mesh.validate(verbose=True)
    object = bpy.data.objects.new("Cod_Vita_Mesh", mesh)
    scene = bpy.context.scene
    scene.collection.objects.link(object)

def GetModelOffset(fileobject):
    fileobject.seek(12,0) #reading end of the file directory so we can jmp from it
    EndOfFileDirectoryOffsetint = ReadInt32(fileobject)
    fileobject.seek(256,0) #looking for FFFF7FFF for other offsets
    FFBYTECONFIRM = 0
    #FFBYTE = b'\xff\xff\x7f\xff' \xff\x7f\xff
    i=0
    for i in range (200):
        
        FFBYTE = fileobject.read(1)
        if FFBYTE == b'\xff':
            FFBYTECONFIRM = fileobject.read(3)
            print(FFBYTECONFIRM)
            break
            
        if i == 199: 
            
            print("byte not found, returning")
            return          

    VerticesAndFacesSizeint = ReadInt32(fileobject) #after FFFF7FFF we have vertices+faces region size
    OffsetFromDirectoryToModelint =  ReadInt32(fileobject) #the offset to jmp from end of directory to model
    TotalOffsetToModel = EndOfFileDirectoryOffsetint + OffsetFromDirectoryToModelint
    print(VerticesAndFacesSizeint)
    print(TotalOffsetToModel)
    return TotalOffsetToModel       



      

    
        

    
        



def ReadDataFromFile(context, filepath):
    fileobjectsmf = open(filepath, "rb")
    #print(fileobjectsmf.read(5))
    modelcomplexcurrent = True
    OffsetToModel = GetModelOffset(fileobjectsmf)
    ImportModel(fileobjectsmf, OffsetToModel, modelcomplexcurrent)
    return
    



class ImportSMF(bpy.types.Operator, ImportHelper):
    bl_idname       = "import_smf.mark";
    bl_label        = "import SMF";
    bl_options      = {'PRESET'};
    
    filename_ext    = ".3do";

    filter_glob: StringProperty(
        default="*.smf",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )
    
    # files = CollectionProperty(
    #     name="3DO files",
    #     type=OperatorFileListElement,
    #     )

    # directory = StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        #print("importer start")
        #then = time.time()
        # for f in self.files:
        #     print(f)
        # print(self.directory)
        ReadDataFromFile(context, self.filepath)
    
        #modelFilePath = self.filepath
        #fileName = modelFilePath[:-3]
        #print("modelFilePath: {0}".format(modelFilePath))
        #model_in = open(modelFilePath, "rb")
        #mesh, materials, shaders = ImportModels(model_in, ntpath.basename(modelFilePath[:-4]))
        #model_in.close()
        


       # now = time.time()
        #print("It took: {0} seconds".format(now-then))
        return {'FINISHED'}








def menu_func_import(self, context):
    self.layout.operator(ImportSMF.bl_idname, text="SMF Mark Style")


def register():
    from bpy.utils import register_class
    register_class(ImportSMF)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    from bpy.utils import unregister_class
    unregister_class(ImportSMF)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()