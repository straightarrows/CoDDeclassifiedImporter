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

def ReadFaceIndex(fileobject, NumFaces):
    fileobject.seek(9,1) #as long as we just finished vertices this should seek to start of faces just fine
    faceindexlist = []
    for i in range(NumFaces): #this is not supposed to be same as floats
        faceindextriple = ReadShortTriple(fileobject)
        #print(faceindextriple)
        faceindexlist.append(faceindextriple)
        #fileobject.seek(1,1)
    return faceindexlist
    

def ReadVertices(fileobject,offsettomodel,ModelType, NumVertices):
    if ModelType == 2 : #if 2C (hex) repeating units
        seekvalue = 32
    if ModelType == 1: #if 28 (hex) repeating units
        seekvalue = 28
    if ModelType == 0:
        seekvalue = 12
    fileobject.seek(offsettomodel+16,0) #the offset to model spits you out 16 bytes before first vertex
    vertexlist = []
    for i in range(NumVertices): 
        vertex = ReadVector(fileobject)
        vertexlist.append(vertex)
        fileobject.seek(seekvalue,1) 

    return vertexlist

def ImportModel(fileobject, offsettomodel, ModelType, NumVertices, NumFaces):
    
    
    vertexlist = ReadVertices(fileobject,offsettomodel,ModelType, NumVertices)
    #print(vertexlist)
    faceindexlist = ReadFaceIndex(fileobject, NumFaces)
    #print(faceindexlist)
    
    mesh = bpy.data.meshes.new("Cod_Vita_Mesh")
    mesh.from_pydata(vertexlist,[],faceindexlist)
    mesh.validate(verbose=True)
    object = bpy.data.objects.new("Cod_Vita_Mesh", mesh)
    scene = bpy.context.scene
    scene.collection.objects.link(object)

def GetModelOffset(fileobject, OffsetFromModelFileStartString, EndofFileDirectoryOffset):
    ###If you want to be slightly more official, you could go to the 
    ###second nsirsrc string section (do this by going to offsets at end of first string section)
    ###find 31 byte and seek 8 bytes to the overall offset of FFFF7FFF
    
    fileobject.seek(256,0) #looking for FFFF7FFF for other offsets
    FFBYTECONFIRM = 0
    #FFBYTE = b'\xff\xff\x7f\xff' \xff\x7f\xff
    
    i=0
    for i in range (50):
        
        FFBYTE = fileobject.read(1)
        if FFBYTE == b'\xff':
            FFBYTECONFIRM = fileobject.read(3)
            print(FFBYTECONFIRM)
            break
            
        if i == 49: 
            
            print("byte not found, returning")
            return          

    VerticesAndFacesSizeint = ReadInt32(fileobject) #after FFFF7FFF we have vertices+faces region size
    OffsetFromNSIHeaderToModelint =  ReadInt32(fileobject) #the offset to jmp from end of NSI Header directory to model
    TotalOffsetToModel = EndofFileDirectoryOffset + OffsetFromNSIHeaderToModelint + OffsetFromModelFileStartString
    #print(VerticesAndFacesSizeint)
    #print(TotalOffsetToModel)
    return TotalOffsetToModel       

def FourBytesAreNonZero(fileobject):
    for i in range (4):
        readbyte = fileobject.read(1)
        if readbyte == 0:
            return False
        else:
            print(i) 
            continue

    return True





def GetDicLoc(fileobject, EndOfFileDirectoryOffset):
    ### Pookey chicken method. we are going seek 158 hex past the end of nsirsrc header
    ###then we are going to search for what I believe is the model tag id
    ###then you take the next 4 bytes as the offset to the real dictionary. 
    ###If those 4 bytes are 0, you take the NEXT 4 and that is usually the dictionary offset 
    fileobject.seek(EndOfFileDirectoryOffset+344,0)
    ###would be nice to make model tag find its own func here

    OffsetToFirstDicbase = 0
    while OffsetToFirstDicbase == 0:
        if FourBytesAreNonZero(fileobject): #dumb way for checking for model tag
            print("do we get here?")
            for x in range(3): #loop thru 12 bytes after model tag to find the offset
                OffsetToFirstDicbase = ReadInt32(fileobject)
                if OffsetToFirstDicbase == 0:
                    continue
                else:
                    break
            
    print(OffsetToFirstDicbase) #is this working? yes
    FirstdicOffset = OffsetToFirstDicbase + EndOfFileDirectoryOffset  
    fileobject.seek(FirstdicOffset + 24, 0) #moving to 1st dic + 18 hex
    OffsetToDDDDirectorybase = ReadInt32(fileobject) #reading 400 from the 1st dic
    DDDDirectoryOffset = OffsetToDDDDirectorybase + EndOfFileDirectoryOffset  #adding the 400 to the string end of header
    print(DDDDirectoryOffset)
    return DDDDirectoryOffset

def GetSubmeshData(DDDDirectoryOffset, fileobject):
    fileobject.seek(DDDDirectoryOffset+8,0)
    NumVertices = ReadInt32(fileobject) 
    OffsetFromModelFileStartString = ReadInt32(fileobject)
    NumFaces = ReadInt32(fileobject)
    ##TO-DO: Loop this through however many submeshes there are in file##
    return NumVertices, OffsetFromModelFileStartString, NumFaces

      

    
def ReadDataFromFile(context, filepath):
    fileobjectsmf = open(filepath, "rb")
    #print(fileobjectsmf.read(5))
    ModelTypeCurrent = 1 #this will need to be changed based off file
    fileobjectsmf.seek(12,0) #reading end of the file directory so we can jmp from it
    EndOfNsiFileDirectoryOffsetint = ReadInt32(fileobjectsmf)
    print(EndOfNsiFileDirectoryOffsetint)
    DDDDirectoryOffset = GetDicLoc(fileobjectsmf, EndOfNsiFileDirectoryOffsetint) #this is working in most cases we throw at it
    NumVertices, OffsetFromModelFileStartString, NumFaces = GetSubmeshData(DDDDirectoryOffset, fileobjectsmf)
    OffsetToModel = GetModelOffset(fileobjectsmf,  OffsetFromModelFileStartString, EndOfNsiFileDirectoryOffsetint ) #adding offset from model file start string should allow us to do submeshes
    ImportModel(fileobjectsmf, OffsetToModel, ModelTypeCurrent, NumVertices, NumFaces)
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