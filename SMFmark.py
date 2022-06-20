bl_info = {
    "name": "Import SMF models",
    "author": "Mark",
    "version": (0,2),
    "blender": (2, 93, 1),
    "location": "File > Export > CoD model (*.smf)",
    "description": 'Import models from "Call of Duty Declassified"',
    "warning": "",
    "wiki_url": "",
    "category": "Import-Export"
}

from pickle import FALSE, TRUE
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

def ReadVector(fileobject, ModelDistancer):
    x = ReadFloat(fileobject)
    y = ReadFloat(fileobject)
    z = ReadFloat(fileobject)
    #print (x)
    #print(y)
    #print(z)
    return Vector([x+ModelDistancer,y,z])

def ReadFaceIndex(fileobject, FacesOverallOffset, NumFaces):
    # NEED TO FIX for this seek below!!!!sometime it is C/12 length! sometimes there is no 8 byte DDDD and the faces start immediately!
    

    
    fileobject.seek(FacesOverallOffset,0) #as long as we just finished vertices this should seek to start of faces just fine
    faceindexlist = []
    for i in range(NumFaces): #this is not supposed to be same as floats
        faceindextriple = ReadShortTriple(fileobject)
        #print(faceindextriple)
        faceindexlist.append(faceindextriple)
        #fileobject.seek(1,1)
    return faceindexlist
    

def ReadVertices(fileobject,FirstVertexOverallOffset,RepeatingVertexUnit, NumVertices, CurrentOverallMesh):
    if RepeatingVertexUnit == 12:
        seekvalue = 0
    if RepeatingVertexUnit == 13: #this is kinda dumb fix for ai weapons which seem to be 13
        seekvalue = 0
    if RepeatingVertexUnit == 16: 
        seekvalue = 4
    if RepeatingVertexUnit == 45 : #if 2C (hex) repeating units
        seekvalue = 32
    if RepeatingVertexUnit == 44 : #if 2C (hex) repeating units
        seekvalue = 32
    if RepeatingVertexUnit == 43 : #another dumb fix since some ai things have literally 1 vertex. this is one is 40
        seekvalue = 28
    if RepeatingVertexUnit == 40: #if 28 (hex) repeating units
        seekvalue = 28
    if RepeatingVertexUnit == 24:
        seekvalue = 12
    if RepeatingVertexUnit == 25:
        seekvalue = 12
    if RepeatingVertexUnit == 36:
        seekvalue = 24
    fileobject.seek(FirstVertexOverallOffset,0) #the offset to model spits you out 16 bytes before first vertex
    vertexlist = []
    ModelDistancer = CurrentOverallMesh*5
    for i in range(NumVertices): 
        vertex = ReadVector(fileobject, ModelDistancer)
        vertexlist.append(vertex)
        fileobject.seek(seekvalue,1) 

    return vertexlist

def ImportModel(fileobject, offsettomodel, OffsetToFaces,FirstVertexOffset, RepeatingVertexUnit, NumVertices, NumFaces, MeshNumber, CurrentOverallMesh):
    
    CurrentVertexOverallOffset = offsettomodel+16
    
    vertexlist = ReadVertices(fileobject,CurrentVertexOverallOffset,RepeatingVertexUnit, NumVertices,CurrentOverallMesh)
    #print(vertexlist)
    
    FacesOverallOffset = FirstVertexOffset + OffsetToFaces
    print(FacesOverallOffset)
    faceindexlist = ReadFaceIndex(fileobject, FacesOverallOffset,NumFaces)
    print(faceindexlist)
    meshstring = "Cod_Vita_Mesh" + str(MeshNumber)
    mesh = bpy.data.meshes.new(meshstring)
    mesh.from_pydata(vertexlist,[],faceindexlist)
    mesh.validate(verbose=True)
    CurrentOverallMeshString = "CoD_Vita_Mesh_" + str(CurrentOverallMesh)+ "_" + str(MeshNumber)
    object = bpy.data.objects.new(CurrentOverallMeshString, mesh)
    scene = bpy.context.scene
    scene.collection.objects.link(object)

def GetModelOffset(fileobject, OffsetFromModelFileStartString, EndofFileDirectoryOffset,CurrentOverallMesh):
    ###If you want to be slightly more official, you could go to the 
    ###second nsirsrc string section (do this by going to offsets at end of first string section)
    ###find 31 byte and seek 8 bytes to the overall offset of FFFF7FFF
    
    fileobject.seek(172,0) #seeking to the 2nd nsi file descriptor (seems to always be AC) to get offset to main file name
    OffsetToNSIFileName =  ReadInt32(fileobject)
    OffsetToOverallModelFileData = CurrentOverallMesh*32
    fileobject.seek(OffsetToNSIFileName+OffsetToOverallModelFileData+100,0) #should alway be 60 hex, 96 dec to FFFF7FFF +4 to the data         

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
            #print(i) 
            continue

    return True

def GetModelTagOffsetArray(fileobject, EndOfNSIFileDirectoryOffset): #REFACTORINGGGG
    fileobject.seek(EndOfNSIFileDirectoryOffset+24,0) #grabbing the number of overall mesh groups
    OverallMeshCount = ReadInt32(fileobject)
    print(OverallMeshCount, "overall meshh count is")
    OffsetFromEndOfNSIToDDDDescriptor = ReadInt32(fileobject) #it is always 140 hex/320 dec to the first DDD descriptor, then you have the number of DDD regions and the offset to the first model tag/model descriptor region
    print(OffsetFromEndOfNSIToDDDDescriptor, "offset should be 320 always")
    
    fileobject.seek(EndOfNSIFileDirectoryOffset+OffsetFromEndOfNSIToDDDDescriptor,0) 
    
    ZeroChecker = 0
    ModelTagCountArray = []
    OffsetToModelTagArray = []
    Counter = 0
    while ZeroChecker == 0: # we could use overall mesh count to stop instead of 0 check
        ModelTagCountArray.append(ReadInt32(fileobject)) # note that this will store a zero 
        if ModelTagCountArray[Counter] == 0:
            ZeroChecker = 1
            ModelTagCountArray.pop()
            break
        OffsetToModelTagArray.append(ReadInt32(fileobject))
        fileobject.seek(8,1)
        Counter = Counter +1

    return OverallMeshCount, ModelTagCountArray, OffsetToModelTagArray



def GetDicLoc(fileobject, EndOfNSIFileDirectoryOffset,CurrentModeltagOffset):
    
    OffsetFromModelTagJmpToActualModelTag = 8
    fileobject.seek(CurrentModeltagOffset+EndOfNSIFileDirectoryOffset+OffsetFromModelTagJmpToActualModelTag,0) #this shoule land us directly on first model tag
    ModelTag = ReadInt32(fileobject)
    fileobject.seek(4,1)
    OffsetToFirstDicbase = ReadInt32(fileobject) #we can expand on thi laters to get all the model tags and their dic offsets, right now we only need first
    if OffsetToFirstDicbase == 0:
        OffsetToFirstDicbase = ReadInt32(fileobject)
            
    print("offset to first dic base is", OffsetToFirstDicbase) #is this working? yes
    #return an array of all the DDD offsets with loop?
    FirstDicOffset = OffsetToFirstDicbase + EndOfNSIFileDirectoryOffset  
    MeshCount = 1
    DicOffsetMeshNumber = 0 #simple count for the number of submeshes
    DDDDirectoriesList = [] #a list of the overall offsets to DDDD directory
    while MeshCount == 1:
        CurrentDicOffset = FirstDicOffset+DicOffsetMeshNumber*32
        #print(CurrentDicOffset)
        fileobject.seek(CurrentDicOffset, 0)
        MeshCount = ReadInt32(fileobject)
        if MeshCount == 1:
            fileobject.seek(CurrentDicOffset + 24, 0) #offset to DDD Direc
            OffsetToDDDDirectorybase = ReadInt32(fileobject)
            print(OffsetToDDDDirectorybase)
            DDDDirectoryOffset = OffsetToDDDDirectorybase + EndOfNSIFileDirectoryOffset
            
            DDDDirectoriesList.append(DDDDirectoryOffset)
            DicOffsetMeshNumber = DicOffsetMeshNumber + 1

    return  DDDDirectoriesList, DicOffsetMeshNumber #also return the dicoffsetmeshnumber? for later for loop


def GetSubmeshData(DDDDirectoryOffset, fileobject):
    fileobject.seek(DDDDirectoryOffset+8,0)
    NumVertices = ReadInt32(fileobject) 
    OffsetFromModelFileStartString = ReadInt32(fileobject)
    NumFaces = ReadInt32(fileobject)
    fileobject.seek(4, 1) #skip the next data point and grab the vertex+ddd size
    FacesOffset = ReadInt32(fileobject) #faces offset from first vertex under smf string
    VertexAndDDDSize = FacesOffset - OffsetFromModelFileStartString #this subtracts the rest of the data so you only have the current submesh vertice+DDD region size
    print ("the size of the vertex and DDD region for this model is",VertexAndDDDSize)
    RepeatingVertexUnit = round(VertexAndDDDSize/NumVertices) #this method is not ideal since DDDD region is sometimes pretty large
    print ("the size of the repeating vertex unit for this model is",RepeatingVertexUnit)
    ##TO-DO: Loop this through however many submeshes there are in file##
    return NumVertices, OffsetFromModelFileStartString, NumFaces, FacesOffset, RepeatingVertexUnit

      

    
def ReadDataFromFile(context, filepath):
    fileobjectsmf = open(filepath, "rb")
    #print(fileobjectsmf.read(5))
    
    fileobjectsmf.seek(12,0) #reading end of the file directory so we can jmp from it
    EndOfNsiFileDirectoryOffsetint = ReadInt32(fileobjectsmf)
    print(EndOfNsiFileDirectoryOffsetint)
    
    OverallMeshCount, ModelTagCountArray, OffsetToModelTagArray = GetModelTagOffsetArray(fileobjectsmf,EndOfNsiFileDirectoryOffsetint)
    #print("overallmeshcount, modeltagcountarray, offsettomodeltagarray", OverallMeshCount, ModelTagCountArray[0], OffsetToModelTagArray[0],OffsetToModelTagArray[1])
    for CurrentOverallMesh in range(OverallMeshCount):
        CurrentModeltagOffset = OffsetToModelTagArray[CurrentOverallMesh]
        print ("current modeltag index offset", CurrentModeltagOffset)
        DDDDirectoriesList, DicOffsetMeshNumber = GetDicLoc(fileobjectsmf, EndOfNsiFileDirectoryOffsetint,CurrentModeltagOffset) #this is working in most cases we throw at it
    ###start the sub mesh loop here?
        for MeshNumber in range (DicOffsetMeshNumber):
            #print("in for loop", DDDDirectoriesList[i])
            NumVertices, OffsetFromModelFileStartString, NumFaces, OffsetToFaces, RepeatingVertexUnit = GetSubmeshData(DDDDirectoriesList[MeshNumber], fileobjectsmf)
            ### we can take below out of for loop as we just add one thing to it later
            OffsetToModel = GetModelOffset(fileobjectsmf,  OffsetFromModelFileStartString, EndOfNsiFileDirectoryOffsetint, CurrentOverallMesh ) #adding offset from model file start string should allow us to do submeshes
            ###
            if MeshNumber == 0: #want to get offset for the first model
                FirstVertexOffset = OffsetToModel+16
                print(" numvertices, numfaces", NumVertices, NumFaces)
                print( "mesh number is", MeshNumber)
            ImportModel(fileobjectsmf, OffsetToModel, OffsetToFaces, FirstVertexOffset, RepeatingVertexUnit, NumVertices, NumFaces, MeshNumber, CurrentOverallMesh)
        
    ###end submesh loop here?
    return
    



class ImportSMF(bpy.types.Operator, ImportHelper):
    bl_idname       = "import_smf.mark";
    bl_label        = "import SMF";
    bl_options      = {'PRESET'};
    
    filename_ext    = ".smf";

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
    self.layout.operator(ImportSMF.bl_idname, text="Import Models From SMF Files In Call Of Duty: Declassified")


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