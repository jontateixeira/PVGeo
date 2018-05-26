__all__ = [
    # General Stuff
    'ubcExtent3D',
    'placeModelOnMesh',

    # 2D Mesh
    'ubcExtent2D',
    'ubcMesh2D',
    'ubcModel2D',
    'ubcMeshData2D',

    # 3D Mesh
    'ubcMesh3D',
    'ubcModel3D',
    'ubcMeshData3D',

    # OcTree
    'ubcOcTree']

import numpy as np
import struct
import csv
import os
from vtk.util import numpy_support as nps
import vtk
# Import Helpers:
from ._helpers import *

#------------------------------------------------------------------#
# General Methods for UBC Formats
#------------------------------------------------------------------#

def ubcExtent3D(FileName):
    """
    Description
    -----------
    Reads the mesh file for the UBC 3D Mesh or OcTree format to get output extents. Computationally inexpensive method to discover whole output extent.

    Parameters
    ----------
    `FileName` : str
    - The mesh filename as an absolute path for the input mesh file in a UBC Format with extents defined on the first line.

    Returns
    -------
    This returns a tuple of the whole extent for the grid to be made of the input mesh file (0,n1-1, 0,n2-1, 0,n3-1). This output should be directly passed to util.SetOutputWholeExtent() when used in programmable filters or source generation on the pipeline.

    """
    # Read in the mesh and set up structure of output grid from mesh file input
    #--- Read in first line of the mesh file ---#
    v = np.array(np.__version__.split('.'), dtype=int)
    if v[0] >= 1 and v[1] >= 10:
        # max_rows in numpy versions >= 1.10
        fileLines = np.genfromtxt(FileName, dtype=str, delimiter='\n', comments='!', max_rows=1)
    else:
        # This reads whole file :(
        fileLines = np.genfromtxt(FileName, dtype=str, delimiter='\n', comments='!')
    # Get mesh dimensions
    dim = np.array(fileLines[0].split('!')[0].split(), dtype=int)
    dim = dim[0:3]
    ne,nn,nz = dim[0], dim[1], dim[2]
    return (0,ne, 0,nn, 0,nz)

def placeModelOnMesh(mesh, model, dataNm='Data'):
    """
    Description
    -----------
    Places model data onto a mesh. This is for the UBC Grid data reaers to associate model data with the mesh grid.

    Parameters
    ----------
    `mesh` : vtkRectilinearGrid
    - The vtkRectilinearGrid that is the mesh to place the model data upon.

    `model` : NumPy float array
    - A NumPy float array that holds all of the data to place inside of the mesh's cells.

    `dataNm` : str, optional
    - The name of the model data array once placed on the vtkRectilinearGrid.

    Returns
    -------
    Returns the input vtkRectilinearGrid with model data appended.

    """
    # model.GetNumberOfValues() if model is vtkDataArray
    # Make sure this model file fits the dimensions of the mesh
    ext = mesh.GetExtent()
    n1,n2,n3 = ext[1],ext[3],ext[5]
    if (n1*n2*n3 < len(model)):
        raise Exception('This model file has more data than the given mesh has cells to hold.')
    elif (n1*n2*n3 > len(model)):
        raise Exception('This model file does not have enough data to fill the given mesh\'s cells.')

    # Swap axes because VTK structures the coordinates a bit differently
    #-  This is absolutely crucial!
    #-  Do not play with unless you know what you are doing!
    model = np.reshape(model, (n1,n2,n3))
    model = np.swapaxes(model,0,1)
    model = np.swapaxes(model,0,2)
    model = model.flatten()

    # Convert data to VTK data structure and append to output
    c = nps.numpy_to_vtk(num_array=model,deep=True)
    c.SetName(dataNm)
    # THIS IS CELL DATA! Add the model data to CELL data:
    mesh.GetCellData().AddArray(c)
    return mesh


#------------------------------------------------------------------#
#----------------------     UBC MESH 2D    ------------------------#
#------------------------------------------------------------------#

def _ubcMesh2D_part(FileName):
    # This is a helper method to read file contents of mesh
    fileLines = np.genfromtxt(FileName, dtype=str, delimiter='\n', comments='!')

    def _genTup(sft, n):
        # This reads in the data for a dimension
        pts = []
        disc = []
        for i in range(n):
            ln = fileLines[i+sft].split('!')[0].split()
            if i is 0:
                o = ln[0]
                pts.append(o)
                ln = [ln[1],ln[2]]
            pts.append(ln[0])
            disc.append(ln[1])
        return pts, disc

    # Get the number of lines for each dimension
    nx = int(fileLines[0].split('!')[0])
    nz = int(fileLines[nx+1].split('!')[0])

    # Get the origins and tups for both dimensions
    xpts, xdisc = _genTup(1, nx)
    zpts, zdisc = _genTup(2+nx, nz)

    return xpts, xdisc, zpts, zdisc

def ubcExtent2D(FileName):
    """
    Description
    -----------
    Reads the mesh file for the UBC 2D Mesh format to get output extents.

    Parameters
    ----------
    `FileName` : str
    - The mesh filename as an absolute path for the input mesh file in a UBC 2D Mesh Format.

    Returns
    -------
    This returns a tuple of the whole extent for the grid to be made of the input mesh file (0,n1-1, 0,n2-1, 0,n3-1). This output should be directly passed to util.SetOutputWholeExtent() when used in programmable filters or source generation on the pipeline.

    """
    # Read in data from file
    xpts, xdisc, zpts, zdisc = _ubcMesh2D_part(FileName)

    nx = np.sum(np.array(xdisc,dtype=int))+1
    nz = np.sum(np.array(zdisc,dtype=int))+1

    return (0,nx, 0,1,  0,nz)

def ubcMesh2D(FileName, pdo=None):
    """
    Description
    -----------
    This method reads a UBC 2D Mesh file and builds an empty vtkRectilinearGrid for data to be inserted into. [Format Specs](http://giftoolscookbook.readthedocs.io/en/latest/content/fileFormats/mesh2Dfile.html)

    Parameters
    ----------
    `FileName` : str
    - The mesh filename as an absolute path for the input mesh file in UBC 3D Mesh Format.

    `pdo` : vtk.vtkRectilinearGrid, optional
    - The output data object

    Returns
    -------
    Returns a vtkRectilinearGrid generated from the UBC 3D Mesh grid. Mesh is defined by the input mesh file. No data attributes here, simply an empty mesh. Use the placeModelOnMesh() method to associate with model data.

    """
    if pdo is None:
        pdo = vtk.vtkRectilinearGrid() # vtkRectilinearGrid

    # Read in data from file
    xpts, xdisc, zpts, zdisc = _ubcMesh2D_part(FileName)

    nx = np.sum(np.array(xdisc,dtype=int))+1
    nz = np.sum(np.array(zdisc,dtype=int))+1

    # Now generate the vtkRectilinear Grid
    def _genCoords(pts, disc):
        c = [float(pts[0])]
        for i in range(len(pts)-1):
            start = float(pts[i])
            stop = float(pts[i+1])
            num = int(disc[i])
            w = (stop-start)/num

            for j in range(1,num):
                c.append(start + (j)*w)
            c.append(stop)
        c = np.array(c,dtype=float)
        return nps.numpy_to_vtk(num_array=c,deep=True)

    xcoords = _genCoords(xpts, xdisc)
    zcoords = _genCoords(zpts, zdisc)
    ycoords = nps.numpy_to_vtk(num_array=np.zeros(1),deep=True)

    pdo.SetDimensions(nx,2,nz) # note this subtracts 1
    pdo.SetXCoordinates(xcoords)
    pdo.SetYCoordinates(ycoords)
    pdo.SetZCoordinates(zcoords)

    return pdo

def ubcModel2D(FileName):
    """
    Description
    -----------
    Reads a 2D model file and returns a 1D NumPy float array. Use the placeModelOnMesh() method to associate with a grid.

    Parameters
    ----------
    `FileName` : str
    - The model filename as an absolute path for the input model file in UBCMesh Model Format.

    Returns
    -------
    Returns a NumPy float array that holds the model data read from the file. Use the placeModelOnMesh() method to associate with a grid.
    """
    fileLines = np.genfromtxt(FileName, dtype=str, delimiter='\n', comments='!')
    dim = np.array(fileLines[0].split(), dtype=int)
    data = np.genfromtxt((line.encode('utf8') for line in fileLines[1::]), dtype=np.float)
    if np.shape(data)[0] != dim[1] and np.shape(data)[1] != dim[0]:
        raise Exception('Mode file `%s` improperly formatted.' % FileName)
    return data.flatten(order='F')

def ubcMeshData2D(FileName_Mesh, FileName_Model, dataNm='', pdo=None):
    """
    Description
    -----------
    UBC Mesh 2D models are defined using a 2-file format. The "mesh" file describes how the data is descritized. The "model" file lists the physical property values for all cells in a mesh. A model file is meaningless without an associated mesh file.

    Parameters
    ----------
    `FileName_Mesh` : str
    - The mesh filename as an absolute path for the input mesh file in UBC 2D Mesh Format

    `FileName_Model` : str
    - The model filename as an absolute path for the input model file in UBC 2D Model Format.

    `dataNm` : str, optional
    - The name of the model data array once placed on the vtkRectilinearGrid.

    Returns
    -------
    Returns a vtkRectilinearGrid generated from the UBC 2D Mesh grid. Mesh is defined by the input mesh file. Cell data is defined by the input model file.

    """
    # If no name given for data by user, use the basename of the file
    if dataNm == '':
        dataNm = os.path.basename(FileName_Model)
    # Construct/read the mesh
    mesh = ubcMesh2D(FileName_Mesh, pdo=pdo)
    # Read the model data
    model = ubcModel2D(FileName_Model)
    # Place the model data onto the mesh
    grd = placeModelOnMesh(mesh, model, dataNm)
    return grd


#------------------------------------------------------------------#
#----------------------     UBC MESH 3D    ------------------------#
#------------------------------------------------------------------#

def ubcMesh3D(FileName, pdo=None):
    """
    Description
    -----------
    This method reads a UBC 3D Mesh file and builds an empty vtkRectilinearGrid for data to be inserted into.

    Parameters
    ----------
    `FileName` : str
    - The mesh filename as an absolute path for the input mesh file in UBC 3D Mesh Format.

    `pdo` : vtk.vtkRectilinearGrid, optional
    - The output data object

    Returns
    -------
    Returns a vtkRectilinearGrid generated from the UBC 3D Mesh grid. Mesh is defined by the input mesh file. No data attributes here, simply an empty mesh. Use the placeModelOnMesh() method to associate with model data.

    """
    if pdo is None:
        pdo = vtk.vtkRectilinearGrid() # vtkRectilinearGrid

    #--- Read in the mesh ---#
    fileLines = np.genfromtxt(FileName, dtype=str,
        delimiter='\n', comments='!')

    # Get mesh dimensions
    dim = np.array(fileLines[0].
        split('!')[0].split(), dtype=int)
    dim = (dim[0]+1, dim[1]+1, dim[2]+1)

    # The origin corner (Southwest-top)
    #- Remember UBC format specifies down as the positive Z
    #- Easting, Northing, Altitude
    oo = np.array(
        fileLines[1].split('!')[0].split(),
        dtype=float
    )
    oe,on,oz = oo[0],oo[1],oo[2]

    vv = [None, None, None]
    # Now extract cell sizes
    for i in range(3):
        # i+2 for file lines because we already dealt with first 2 lines
        spac_str = fileLines[i+2].split('!')[0].split()
        # Now check if there are any of the repeating spacings
        #- format example: 5*10.0 for five cells of width 10.0
        ins_idx = []
        ins_spac = []
        for j in range(len(spac_str)):
            if '*' in spac_str[j]:
                parsed = spac_str[j].split('*')
                ins_idx.append(j)
                num, dist = int(parsed[0]), parsed[1]
                ins = [dist]*num
                ins_spac.append(ins)
        for j in range(len(ins_idx)):
            del spac_str[ins_idx[j]] # remove the parsed element
            # Now insert the spacings into the spacing array
            for k in range(len(ins_spac[j])):
                spac_str.insert(ins_idx[j]+k,ins_spac[j][k])
        # Now make a numpy flaot array
        spac = np.array(spac_str, dtype=float)
        # Now check that we have correct number widths for given dimension
        if len(spac) != dim[i]-1:
            raise Exception('More spacings specifed than extent defined allows for dimension %d' % i)
        # Now generate the coordinates for this dimension
        s = np.zeros(dim[i])
        s[0] = oo[i]
        for j in range(1, dim[i]):
            if (i == 2):
                # Z dimension (down is positive Z!)
                #  TODO: what is the correct way to do this?
                s[j] = s[j-1] + spac[j-1]
            else:
                # X and Y dimensions
                s[j] = s[j-1] + spac[j-1]
        # Convert to VTK array for setting coordinates
        vv[i] = nps.numpy_to_vtk(num_array=s,deep=True)

    # Set the dims and coordinates for the output
    pdo.SetDimensions(dim[0],dim[1],dim[2])
    pdo.SetXCoordinates(vv[0])
    pdo.SetYCoordinates(vv[1])
    pdo.SetZCoordinates(vv[2])

    return pdo

def ubcModel3D(FileName):
    """
    Description
    -----------
    Reads the 3D model file and returns a 1D NumPy float array. Use the placeModelOnMesh() method to associate with a grid.

    Parameters
    ----------
    `FileName` : str
    - The model filename as an absolute path for the input model file in UBC 3D Model Model Format.

    Returns
    -------
    Returns a NumPy float array that holds the model data read from the file. Use the placeModelOnMesh() method to associate with a grid.
    """
    fileLines = np.genfromtxt(FileName, dtype=str, delimiter='\n', comments='!')
    data = np.genfromtxt((line.encode('utf8') for line in fileLines), dtype=np.float)
    return data

def ubcMeshData3D(FileName_Mesh, FileName_Model, dataNm='', pdo=None):
    """
    Description
    -----------
    UBC Mesh 3D models are defined using a 2-file format. The "mesh" file describes how the data is descritized. The "model" file lists the physical property values for all cells in a mesh. A model file is meaningless without an associated mesh file.

    Parameters
    ----------
    `FileName_Mesh` : str
    - The mesh filename as an absolute path for the input mesh file in UBC 3D Mesh Format

    `FileName_Model` : str
    - The model filename as an absolute path for the input model file in UBC 3D Model Format.

    `dataNm` : str, optional
    - The name of the model data array once placed on the vtkRectilinearGrid.

    Returns
    -------
    Returns a vtkRectilinearGrid generated from the UBC 3D Mesh grid. Mesh is defined by the input mesh file. Cell data is defined by the input model file.

    """
    # If no name given for data by user, use the basename of the file
    if dataNm == '':
        dataNm = os.path.basename(FileName_Model)
    # Construct/read the mesh
    mesh = ubcMesh3D(FileName_Mesh, pdo=pdo)
    # Read the model data
    model = ubcModel3D(FileName_Model)
    # Place the model data onto the mesh
    grd = placeModelOnMesh(mesh, model, dataNm)
    return grd



#------------------------------------------------------------------#
#-----------------------    UBC OcTree    -------------------------#
#------------------------------------------------------------------#

def ubcOcTree(FileName, dataNm='', pdo=None):
    """
    Description
    -----------
    This method reads a UBC OcTree Mesh file and builds a vtkUnstructuredGrid of the data in the file. This method generates the vtkUnstructuredGrid without any data attributes. 

    Parameters
    ----------
    `FileName` : str
    - The mesh filename as an absolute path for the input mesh file in UBC OcTree format.

    `dataNm` : str, optional
    - The name of the model data array once placed on the vtkRectilinearGrid.

    `pdo` : vtk.vtkUnstructuredGrid, optional
    - A pointer to the output data object.

    Returns
    -------
    Returns a vtkUnstructuredGrid generated from the UBCMesh grid. Mesh is defined by the input mesh file. No data attributes here, simply an empty mesh. Use the placeModelOnMesh() method to associate with model data.

    """
    if pdo is None:
        pdo = vtk.vtkUnstructuredGrid() # vtkUnstructuredGrid

    #--- Read in the mesh ---#
    fileLines = np.genfromtxt(FileName, dtype=str,
        delimiter='\n', comments='!')

    # Get mesh dimensions
    dim = np.array(fileLines[0].
        split('!')[0].split(), dtype=int)
    # First three values are the number of cells in the core mesh and remaining 6 values are padding for the core region.
    pad = dim[3:6] # TODO: check if there because optional... might throw error if not there
    dim = dim[0:3]
    ne,nn,nz = dim[0], dim[1], dim[2]
    if np.unique(dim).size > 1:
        raise Exception('OcTree meshes must have the same number of cells in all directions.')

    # The origin corner (Southwest-top)
    #- Remember UBC format specifies down as the positive Z
    #- Easting, Northing, Altitude
    oo = np.array(
        fileLines[1].split('!')[0].split(),
        dtype=float
    )
    oe,on,oz = oo[0],oo[1],oo[2]

    # Widths of the core cells in the Easting, Northing, and Vertical directions.
    ww = np.array(
        fileLines[2].split('!')[0].split(),
        dtype=float
    )
    we,wn,wz = ww[0],ww[1],ww[2]

    # Number of cells in OcTree mesh
    numCells = np.array(
        fileLines[3].split('!')[0].split(),
        dtype=float
    )

    # Read the remainder of the file containing the index arrays
    indArr = np.genfromtxt((line.encode('utf8') for line in fileLines[4::]), dtype=np.int)

    ################
    # TODO: Construct vtk.vtkUnstructuredGrid() of data that we just read from file
    # NOTE: We want to use the `pdo` object already assigned as a vtkUnstructuredGrid
    print('This reader is not fully implemented yet')
    print(indArr)
    ################

    return pdo
