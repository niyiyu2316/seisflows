#
# This is Seisflows
#
# See LICENCE file
#
###############################################################################

# Import system modules
import sys

# Import Numpy
import numpy as np

# Local imports
from os.path import join
from seisflows.tools import unix
from seisflows.tools.tools import exists
from seisflows.config import ParameterError

try:
    PAR = sys.modules['seisflows_parameters']
    PATH = sys.modules['seisflows_paths']
#optimize = sys.modules['seisflows_optimize']

    system = sys.modules['seisflows_system']
    solver = sys.modules['seisflows_solver']
except:
    print("Check parameters and paths.")


class base(object):
    """ Regularization, smoothing, sharpening, masking and related operations
      on models or gradients
    """

    def check(self):
        """ Checks parameters and paths
        """
        if 'SMOOTH' not in PAR:
            setattr(PAR, 'SMOOTH', 0.)

        if 'MASK' not in PATH:
            setattr(PATH, 'MASK', None)

        if PATH.MASK:
            assert exists(PATH.MASK)

    def setup(self):
        """ Placeholder for initialization or setup tasks
        """
        pass

    def write_gradient(self, path):
        """
        Combines contributions from individual sources and material parameters
        to get the gradient, and optionally applies user-supplied scaling

        :input path: directory from which kernels are read and to which
                     gradient is written
        """
        if not exists(path):
            raise Exception

        # because processing operations can be quite expensive, they must be
        # run through the HPC system interface; processing does not involve
        # embarassingly parallel tasks, we use system.run_single instead of
        # system.run

        #Here's where run smooth process.
        system.run_single('postprocess', 'process_kernels',
                          path=path+'/kernels',
                          parameters=solver.parameters)

        gradient = solver.load(
            path+'/'+'kernels/sum', suffix='_kernel')

        # merge into a single vector
        gradient = solver.merge(gradient)

        # convert to absolute perturbations, log dm --> dm
        # see Eq.13 Tromp et al 2005
        gradient *= solver.merge(solver.load(path + '/' + 'model'))
        if PATH.MASK:
            # to scale the gradient, users can supply "masks" by exactly
            # mimicking the file format in which models are stored
            mask = solver.merge(solver.load(PATH.MASK))

            # while both masking and preconditioning involve scaling the
            # gradient, they are fundamentally different operations:
            # masking is ad hoc, preconditioning is a change of variables;
            # see Modrak & Tromp 2016 GJI Seismic waveform inversion best
            # practices: regional,global and exploration test cases
            solver.save(solver.split(gradient),
                        path + '/' + 'gradient_nomask',
                        parameters=solver.parameters,
                        suffix='_kernel')

            solver.save(solver.split(gradient*mask),
                        path + '/' + 'gradient',
                        parameters=solver.parameters,
                        suffix='_kernel')

        else:
            solver.save(solver.split(gradient),
                        path + '/' + 'gradient',
                        parameters=solver.parameters,
                        suffix='_kernel')

    def process_kernels(self, path, parameters):
        """
        Sums kernels from individual sources, with optional smoothing

        :input path: directory containing sensitivity kernels
        :input parameters: list of material parameters e.g. ['vp','vs']
        """
        if not exists(path):
            raise Exception
        
        if PAR.SMOOTH > 0:
            solver.combine(
                   input_path=path,
                   output_path=path+'/'+'sum_nosmooth',
                   parameters=parameters)
            #if optimize.iter == 1:
            for PROC in range(PAR.NPROC):
                unix.cp(src = PATH.MODEL_INIT + '/proc%06d_NSPEC_ibool.bin' % PROC, dst = path + '/' + 'sum_nosmooth'+ '/proc%06d_NSPEC_ibool.bin' % PROC)
                unix.cp(src = PATH.MODEL_INIT + '/proc%06d_jacobian.bin' % PROC, dst = path + '/' + 'sum_nosmooth'+ '/proc%06d_jacobian.bin' % PROC)
                unix.cp(src = PATH.MODEL_INIT + '/proc%06d_x.bin' % PROC, dst = path + '/' + 'sum_nosmooth'+ '/proc%06d_x.bin' % PROC)
                unix.cp(src = PATH.MODEL_INIT + '/proc%06d_z.bin' % PROC, dst = path + '/' + 'sum_nosmooth'+ '/proc%06d_z.bin' % PROC)
            solver.smooth(
                   input_path=path+'/'+'sum_nosmooth',
                   output_path=path+'/'+'sum',
                   parameters=parameters,
                   span=PAR.SMOOTH)
        else:
            solver.combine(
                   input_path=path,
                   output_path=path+'/'+'sum',
                   parameters=parameters)
