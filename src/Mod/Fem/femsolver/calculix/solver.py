# ***************************************************************************
# *   Copyright (c) 2017 Bernd Hahnebach <bernd@bimstatik.org>              *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

__title__ = "FreeCAD FEM solver object CalculiX"
__author__ = "Bernd Hahnebach"
__url__ = "https://www.freecad.org"

## @package SolverCalculix
#  \ingroup FEM

import glob
import os

import FreeCAD

from . import tasks
from .. import run
from .. import solverbase
from femtools import femutils

if FreeCAD.GuiUp:
    import FemGui

ANALYSIS_TYPES = ["static", "frequency", "thermomech", "check", "buckling"]


def create(doc, name="SolverCalculiX"):
    return femutils.createObject(doc, name, Proxy, ViewProxy)


class _BaseSolverCalculix:

    def on_restore_of_document(self, obj):
        temp_analysis_type = obj.AnalysisType
        obj.AnalysisType = ANALYSIS_TYPES
        if temp_analysis_type in ANALYSIS_TYPES:
            obj.AnalysisType = temp_analysis_type
        else:
            FreeCAD.Console.PrintWarning(
                f"Analysis type {temp_analysis_type} not found. Standard is used.\n"
            )
            obj.AnalysisType = ANALYSIS_TYPES[0]

        self.add_attributes(obj)

    def add_attributes(self, obj):
        if not hasattr(obj, "AnalysisType"):
            obj.addProperty(
                "App::PropertyEnumeration", "AnalysisType", "Fem", "Type of the analysis"
            )
            obj.AnalysisType = ANALYSIS_TYPES
            obj.AnalysisType = ANALYSIS_TYPES[0]

        if not hasattr(obj, "GeometricalNonlinearity"):
            choices_geom_nonlinear = ["linear", "nonlinear"]
            obj.addProperty(
                "App::PropertyEnumeration",
                "GeometricalNonlinearity",
                "Fem",
                "Set geometrical nonlinearity",
            )
            obj.GeometricalNonlinearity = choices_geom_nonlinear
            obj.GeometricalNonlinearity = choices_geom_nonlinear[0]

        if not hasattr(obj, "MaterialNonlinearity"):
            choices_material_nonlinear = ["linear", "nonlinear"]
            obj.addProperty(
                "App::PropertyEnumeration",
                "MaterialNonlinearity",
                "Fem",
                "Set material nonlinearity",
            )
            obj.MaterialNonlinearity = choices_material_nonlinear
            obj.MaterialNonlinearity = choices_material_nonlinear[0]

        if not hasattr(obj, "EigenmodesCount"):
            obj.addProperty(
                "App::PropertyIntegerConstraint",
                "EigenmodesCount",
                "Fem",
                "Number of modes for frequency calculations",
            )
            obj.EigenmodesCount = (10, 1, 100, 1)

        if not hasattr(obj, "EigenmodeLowLimit"):
            obj.addProperty(
                "App::PropertyFloatConstraint",
                "EigenmodeLowLimit",
                "Fem",
                "Low frequency limit for eigenmode calculations",
            )
            obj.EigenmodeLowLimit = (0.0, 0.0, 1000000.0, 10000.0)

        if not hasattr(obj, "EigenmodeHighLimit"):
            obj.addProperty(
                "App::PropertyFloatConstraint",
                "EigenmodeHighLimit",
                "Fem",
                "High frequency limit for eigenmode calculations",
            )
            obj.EigenmodeHighLimit = (1000000.0, 0.0, 1000000.0, 10000.0)

        if not hasattr(obj, "IterationsMaximum"):
            help_string_IterationsMaximum = (
                "Maximum Number of iterations in each time step before stopping jobs"
            )
            obj.addProperty(
                "App::PropertyIntegerConstraint",
                "IterationsMaximum",
                "Fem",
                help_string_IterationsMaximum,
            )
            obj.IterationsMaximum = 2000

        if hasattr(obj, "IterationsThermoMechMaximum"):
            obj.IterationsMaximum = obj.IterationsThermoMechMaximum
            obj.removeProperty("IterationsThermoMechMaximum")

        if not hasattr(obj, "BucklingFactors"):
            obj.addProperty(
                "App::PropertyIntegerConstraint",
                "BucklingFactors",
                "Fem",
                "Calculates the lowest buckling modes to the corresponding buckling factors",
            )
            obj.BucklingFactors = 1

        if not hasattr(obj, "TimeInitialStep"):
            obj.addProperty(
                "App::PropertyFloatConstraint", "TimeInitialStep", "Fem", "Initial time steps"
            )
            obj.TimeInitialStep = 0.01

        if not hasattr(obj, "TimeEnd"):
            obj.addProperty("App::PropertyFloatConstraint", "TimeEnd", "Fem", "End time analysis")
            obj.TimeEnd = 1.0

        if not hasattr(obj, "TimeMinimumStep"):
            obj.addProperty(
                "App::PropertyFloatConstraint", "TimeMinimumStep", "Fem", "Minimum time step"
            )
            obj.TimeMinimumStep = 0.00001

        if not hasattr(obj, "TimeMaximumStep"):
            obj.addProperty(
                "App::PropertyFloatConstraint", "TimeMaximumStep", "Fem", "Maximum time step"
            )
            obj.TimeMaximumStep = 1.0

        if not hasattr(obj, "ThermoMechSteadyState"):
            obj.addProperty(
                "App::PropertyBool",
                "ThermoMechSteadyState",
                "Fem",
                "Choose between steady state thermo mech or transient thermo mech analysis",
            )
            obj.ThermoMechSteadyState = True

        if not hasattr(obj, "IterationsControlParameterTimeUse"):
            obj.addProperty(
                "App::PropertyBool",
                "IterationsControlParameterTimeUse",
                "Fem",
                "Use the user defined time incrementation control parameter",
            )
            obj.IterationsControlParameterTimeUse = False

        if not hasattr(obj, "SplitInputWriter"):
            obj.addProperty(
                "App::PropertyBool", "SplitInputWriter", "Fem", "Split writing of ccx input file"
            )
            obj.SplitInputWriter = False

        if not hasattr(obj, "IterationsControlParameterIter"):
            control_parameter_iterations = (
                "{I_0},{I_R},{I_P},{I_C},{I_L},{I_G},{I_S},{I_A},{I_J},{I_T}".format(
                    I_0=4,
                    I_R=8,
                    I_P=9,
                    I_C=200,  # ccx default = 16
                    I_L=10,
                    I_G=400,  # ccx default = 4
                    I_S="",
                    I_A=200,  # ccx default = 5
                    I_J="",
                    I_T="",
                )
            )
            obj.addProperty(
                "App::PropertyString",
                "IterationsControlParameterIter",
                "Fem",
                "User defined time incrementation iterations control parameter",
            )
            obj.IterationsControlParameterIter = control_parameter_iterations

        if not hasattr(obj, "IterationsControlParameterCutb"):
            control_parameter_cutback = "{D_f},{D_C},{D_B},{D_A},{D_S},{D_H},{D_D},{W_G}".format(
                D_f=0.25,
                D_C=0.5,
                D_B=0.75,
                D_A=0.85,
                D_S="",
                D_H="",
                D_D=1.5,
                W_G="",
            )
            obj.addProperty(
                "App::PropertyString",
                "IterationsControlParameterCutb",
                "Fem",
                "User defined time incrementation cutbacks control parameter",
            )
            obj.IterationsControlParameterCutb = control_parameter_cutback

        if not hasattr(obj, "IterationsUserDefinedIncrementations"):
            stringIterationsUserDefinedIncrementations = (
                "Set to True to switch off the ccx automatic incrementation completely "
                "(ccx parameter DIRECT). Use with care. Analysis may not converge!"
            )
            obj.addProperty(
                "App::PropertyBool",
                "IterationsUserDefinedIncrementations",
                "Fem",
                stringIterationsUserDefinedIncrementations,
            )
            obj.IterationsUserDefinedIncrementations = False

        if not hasattr(obj, "IterationsUserDefinedTimeStepLength"):
            help_string_IterationsUserDefinedTimeStepLength = (
                "Set to True to use the user defined time steps. "
                "They are set with TimeInitialStep, TimeEnd, TimeMinimum and TimeMaximum"
            )
            obj.addProperty(
                "App::PropertyBool",
                "IterationsUserDefinedTimeStepLength",
                "Fem",
                help_string_IterationsUserDefinedTimeStepLength,
            )
            obj.IterationsUserDefinedTimeStepLength = False

        if not hasattr(obj, "MatrixSolverType"):
            known_ccx_solver_types = [
                "default",
                "pastix",
                "pardiso",
                "spooles",
                "iterativescaling",
                "iterativecholesky",
            ]
            obj.addProperty(
                "App::PropertyEnumeration", "MatrixSolverType", "Fem", "Type of solver to use"
            )
            obj.MatrixSolverType = known_ccx_solver_types
            obj.MatrixSolverType = known_ccx_solver_types[0]

        if not hasattr(obj, "BeamShellResultOutput3D"):
            obj.addProperty(
                "App::PropertyBool",
                "BeamShellResultOutput3D",
                "Fem",
                "Output 3D results for 1D and 2D analysis ",
            )
            obj.BeamShellResultOutput3D = True

        if not hasattr(obj, "BeamReducedIntegration"):
            obj.addProperty(
                "App::PropertyBool",
                "BeamReducedIntegration",
                "Fem",
                "Set to True to use beam elements with reduced integration",
            )
            obj.BeamReducedIntegration = True

        if not hasattr(obj, "OutputFrequency"):
            obj.addProperty(
                "App::PropertyIntegerConstraint",
                "OutputFrequency",
                "Fem",
                "Set the output frequency in increments",
            )
            obj.OutputFrequency = 1

        if not hasattr(obj, "ModelSpace"):
            model_space_types = ["3D", "plane stress", "plane strain", "axisymmetric"]
            obj.addProperty("App::PropertyEnumeration", "ModelSpace", "Fem", "Type of model space")
            obj.ModelSpace = model_space_types

        if not hasattr(obj, "ThermoMechType"):
            thermomech_types = ["coupled", "uncoupled", "pure heat transfer"]
            obj.addProperty(
                "App::PropertyEnumeration",
                "ThermoMechType",
                "Fem",
                "Type of thermomechanical analysis",
            )
            obj.ThermoMechType = thermomech_types


class Proxy(solverbase.Proxy, _BaseSolverCalculix):
    """The Fem::FemSolver's Proxy python type, add solver specific properties"""

    Type = "Fem::SolverCalculix"

    def __init__(self, obj):
        super().__init__(obj)
        obj.Proxy = self
        self.add_attributes(obj)

    def onDocumentRestored(self, obj):
        self.on_restore_of_document(obj)

    def createMachine(self, obj, directory, testmode=False):
        return run.Machine(
            solver=obj,
            directory=directory,
            check=tasks.Check(),
            prepare=tasks.Prepare(),
            solve=tasks.Solve(),
            results=tasks.Results(),
            testmode=testmode,
        )

    def editSupported(self):
        return True

    def edit(self, directory):
        pattern = os.path.join(directory, "*.inp")
        FreeCAD.Console.PrintMessage(f"{pattern}\n")
        f = glob.glob(pattern)[0]
        FemGui.open(f)

    def execute(self, obj):
        return


class ViewProxy(solverbase.ViewProxy):
    pass


"""
Should there be some equation object for Calculix too?

Necessarily yes! The properties GeometricalNonlinearity,
MaterialNonlinearity, ThermoMechSteadyState might be moved
to the appropriate equation.

Furthermore the material Category should not be used in writer.
See common material object for more information. The equation
should used instead to get this information needed in writer.
"""
