# helpers.py
from Autodesk.Revit.DB import DisplayUnitType

class RevitHelper:
    @staticmethod
    def conversion(units):
        return 304.8 if units == DisplayUnitType.DUT_MILLIMETERS else 30.48
