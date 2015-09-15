# Copyright 2014, 2015 The ODL development group
#
# This file is part of ODL.
#
# ODL is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ODL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ODL.  If not, see <http://www.gnu.org/licenses/>.

# Imports for common Python 2/3 codebase
from __future__ import print_function, division, absolute_import
from future import standard_library
standard_library.install_aliases()

from math import sin, cos, pi
import numpy as np

import odl.operator.operator as OP
from odl.space.default import L2
import odl.space.cuda as cs
import odl.sets.product as ps
from odl.sets.domain import Rectangle, Cube
from odl.discr.default import l2_uniform_discretization
import SimRec2DPy as SR
import GPUMCIPy as gpumci
from odl.util.testutils import Timer

import matplotlib.pyplot as plt


class ProjectionGeometry3D(object):
    """ Geometry for a specific projection
    """
    def __init__(self, sourcePosition, detectorOrigin, pixelDirectionU,
                 pixelDirectionV):
        self.sourcePosition = sourcePosition
        self.detectorOrigin = detectorOrigin
        self.pixelDirectionU = pixelDirectionU
        self.pixelDirectionV = pixelDirectionV


class CudaSimpleMCProjector(OP.Operator):
    """ A projector that creates several projections as defined by geometries
    """
    def __init__(self, volumeOrigin, voxelSize, nVoxels, nPixels, geometries,
                 domain, range):
        self.geometries = geometries
        self.domain = domain
        self.range = range
        self.forward = gpumci.SimpleMC(nVoxels, volumeOrigin, voxelSize,
                                       nPixels)

    def _apply(self, data, out):
        # Create projector
        mat = data.asarray() > 0
        materials = cs.CudaFn(data.space.dim, np.uint8).element(
            mat.flatten(order='F'))
        self.forward.setData(data.ntuple.data_ptr, materials.data_ptr)

        # Project all geometries
        for i in range(len(self.geometries)):
            geo = self.geometries[i]

            with Timer("projecting"):
                self.forward.project(geo.sourcePosition, geo.detectorOrigin,
                                     geo.pixelDirectionU, geo.pixelDirectionV,
                                     out[i][0].ntuple.data_ptr,
                                     out[i][1].ntuple.data_ptr)


# Set geometry parameters
volumeSize = np.array([200.0, 200.0, 200.0])
volumeOrigin = np.array([-100.0, -100.0, -100.0])

detectorSize = np.array([300.0, 300.0])
detectorOrigin = np.array([-150.0, -150.0])

sourceAxisDistance = 790.0
detectorAxisDistance = 210.0

# Discretization parameters
# nVoxels, nPixels = np.array([10 ,10,10]), np.array([10, 10])
nVoxels, nPixels = np.array([100, 100, 100]), np.array([100, 100])
nProjection = 9

# Scale factors
voxelSize = volumeSize / nVoxels
pixelSize = detectorSize / nPixels

# Define projection geometries
geometries = []
for theta in np.linspace(0, pi, nProjection, endpoint=False):
    x0 = np.array([cos(theta), sin(theta), 0.0])
    y0 = np.array([-sin(theta), cos(theta), 0.0])
    z0 = np.array([0.0, 0.0, 1.0])

    projSourcePosition = -sourceAxisDistance * x0
    projPixelDirectionU = y0 * pixelSize[0]
    projPixelDirectionV = z0 * pixelSize[1]
    projDetectorOrigin = (detectorAxisDistance * x0 +
                          detectorOrigin[0] * y0 +
                          detectorOrigin[1] * z0)
    geometries.append(ProjectionGeometry3D(projSourcePosition,
                                           projDetectorOrigin,
                                           projPixelDirectionU,
                                           projPixelDirectionV))

# Define the space of one projection
projectionSpace = L2(Rectangle([0, 0], detectorSize))

# Discretize projection space
# TODO: specify F ordering!
projectionDisc = l2_uniform_discretization(projectionSpace, nPixels,
                                           impl='cuda')

# Create the data space, which is the Cartesian product of the
# single projection spaces
dataDisc = ps.ProductSpace(ps.ProductSpace(projectionDisc, 2), nProjection)

# Define the reconstruction space
reconSpace = L2(Cube([0, 0, 0], volumeSize))

# Discretize the reconstruction space
reconDisc = l2_uniform_discretization(reconSpace, nVoxels, impl='cuda')

# Create a phantom
phantom = SR.SRPyUtils.phantom(nVoxels[0:2])
phantom = np.repeat(phantom, nVoxels[-1]).reshape(nVoxels)
phantomVec = reconDisc.element(phantom.flatten(order='F'))

# Make the operator
projector = CudaSimpleMCProjector(volumeOrigin, voxelSize, nVoxels, nPixels,
                                  geometries, reconDisc, dataDisc)
result = projector(phantomVec)

nrows, ncols = 3, 3
fig, axes = plt.subplots(nrows=nrows, ncols=ncols)
fig.tight_layout()
figs, axess = plt.subplots(nrows=nrows, ncols=ncols)
figs.tight_layout()
for i, ax, axs in zip(range(nrows*ncols), axes.flat, axess.flat):
    ax.imshow(result[i][0].asarray().reshape(nPixels, order='F').T,
              cmap='bone', origin='lower')
    ax.axis('off')
    axs.imshow(result[i][1].asarray().reshape(nPixels, order='F').T,
               cmap='bone', origin='lower')
    axs.axis('off')

plt.show()
