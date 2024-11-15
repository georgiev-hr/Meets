# sheet_manager.py
from helpers import RevitHelper
from size_determiner import SizeDeterminer
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.DB import *
import clr
import sys

class SheetManager:
    def __init__(self, doc, tb_value, big_dict, select_tb, length_display_unit, size_determiner):
        self.doc = doc
        self.tb_value = tb_value
        self.big_dict = big_dict
        self.select_tb = select_tb
        self.length_display_unit = length_display_unit
        self.size_determiner = size_determiner
    def define_location(self, move, y_move_value, distance_to_move, distance_to_move_y):
        # Set location based on title block type
        # move is the original width of the Crop Region

        offset = 5 if "SD" in self.select_tb else 26
        x_location = ((move / 2 + offset + distance_to_move) / RevitHelper.conversion(self.length_display_unit)) * -1
        y_location = ((y_move_value + distance_to_move_y) * 0.5) / RevitHelper.conversion(self.length_display_unit)

        return XYZ(x_location, y_location, 0)

    def create_sheet(self, key, set_tb, y_move_value, width, move, distance_to_move, distance_to_move_y):
        t = Transaction(self.doc, "Create Sheets")
        t.Start()

        # Create the sheet
        new_sheet = ViewSheet.Create(self.doc, self.tb_value.Id)
        new_sheet.Name = key.Name
        new_sheet.SheetNumber = str(key.Name)

        # Modify Title Block
        title_block_instance = None
        for element in FilteredElementCollector(self.doc, new_sheet.Id).OfCategory(BuiltInCategory.OST_TitleBlocks):
            title_block_instance = element
            break

        if title_block_instance:
            # Assign the new title block type
            title_block_instance.ChangeTypeId(set_tb)
            parameter = title_block_instance.LookupParameter("Sheet Width")
            if parameter and not parameter.IsReadOnly:
                set_width = width / RevitHelper.conversion(self.length_display_unit)

                parameter.Set(set_width)
            else:
                TaskDialog.Show("Warning", "Don't change Parameter Names, Only use standard IPA Title Block Families")
                sys.exit()

        # Define location based on title block type and add view to the sheet
        location = self.define_location(move, y_move_value, distance_to_move, distance_to_move_y)
        Viewport.Create(self.doc, new_sheet.Id, key.Id, location)

        t.Commit()

    def process_sheets_fits_rolls(self, distance_to_move, distance_to_move_y):
        if self.tb_value:
            title_block_family = self.tb_value.Family

            # Collect all types belonging to this family
            family_types = [
                symbol for symbol in FilteredElementCollector(self.doc)
                .OfClass(FamilySymbol)
                .OfCategory(BuiltInCategory.OST_TitleBlocks)
                if symbol.Family.Id == title_block_family.Id
            ]

            # Iterate through each key, value_list in big_dict["fits_rolls"]
            for key, value_list in self.big_dict["fits_rolls"].items():
                adj_width, adj_height = value_list[0], value_list[1]  # Get width and height from list of dict value
                move = value_list[2]

                for tb_type in family_types:
                    name = Element.Name.GetValue(tb_type)
                    height_value = tb_type.LookupParameter("Height").AsDouble() * RevitHelper.conversion(
                        self.length_display_unit)

                    # Check height within tolerance
                    tolerance = 0.5
                    target_height = self.size_determiner.determine_height(
                        adj_height)  # Adjusted height using SizeDeterminer
                    if abs(height_value - target_height) < tolerance and not any(
                            substring in name for substring in ["A0", "A1", "A2", "A3"]):
                        set_tb = tb_type.Id
                        y_move_value = height_value

                        # Create the sheet
                        self.create_sheet(key, set_tb, y_move_value, adj_width, move, distance_to_move, distance_to_move_y)

                        break

    def process_sheets_fits_a(self, distance_to_move, distance_to_move_y):

        # Ensure tb_value and family are defined and accessible
        if self.tb_value:
            title_block_family = self.tb_value.Family

            # Collect all types belonging to this family
            family_types = [
                symbol for symbol in FilteredElementCollector(self.doc)
                .OfClass(FamilySymbol)
                .OfCategory(BuiltInCategory.OST_TitleBlocks)
                if symbol.Family.Id == title_block_family.Id
            ]

            for key, value_list in self.big_dict["fits_a"].items():
                adj_width, adj_height = value_list[0], value_list[1]  # Get width and height from list of dict value
                a_size = value_list[2]
                move = value_list[3]

                for tb_type in family_types:
                    name = Element.Name.GetValue(tb_type)

                    # Check if title block fits within standard "A" sizes
                    if a_size in name:
                        set_tb = tb_type.Id
                        dimensions = {
                            "A0": 84.1,
                            "A1": 59.4,
                            "A2": 42,
                            "A3": 42
                        }
                        y_move_value = [dimensions[a_size]][0]  # Default to 0 if name not found in dimensions

                        # Create the sheet
                        self.create_sheet(key, set_tb, y_move_value, adj_width, move, distance_to_move, distance_to_move_y)

                        break