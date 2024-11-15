# Meets_script.py
import clr
# Add references to Revit API assemblies
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")
import logexporter
from Autodesk.Revit.UI import TaskDialog
from pyrevit import forms
from Autodesk.Revit.DB import *
import sys

doc = __revit__.ActiveUIDocument.Document  # Active Revit document
length_display_unit = doc.GetUnits().GetFormatOptions(UnitType.UT_Length).DisplayUnits




from view_collector import ViewCollector
from size_determiner import SizeDeterminer
from helpers import RevitHelper
from sheet_manager import SheetManager



# Initialize Classes
view_collector = ViewCollector(doc)
size_determiner = SizeDeterminer(length_display_unit)
helper = RevitHelper

# Get unique phases and let the user select
unique_phases = view_collector.get_unique_phases()
# Let the user select a phase from the unique list
phase = forms.SelectFromList.show(unique_phases, multiselect=False, title='Select Phase', button_name='Select Phase')


filtered_views = view_collector.filter_views_by_phase(phase)
views_not_in_sheets = view_collector.filter_views_not_on_sheets(filtered_views)

# Sort all views by their names
views_not_in_sheets.sort(key=lambda x: x.get_Parameter(BuiltInParameter.VIEW_NAME).AsString())

sort = ["FloorPlan",
              "AreaPlan",
              "Section",
              "Elevation",
              "CeilingPlan",
              "ThreeD",
              ]

select_view_type = forms.SelectFromList.show(sort,
                                multiselect=False,
                                title='Select View Type',
                                button_name='Select View Type')

# Convert the selected string to corresponding DB.ViewType enum
view_type_enum = getattr(ViewType, select_view_type, None)

# Filter and collect only views that match the selected view type
filtered_views_list = [v for v in views_not_in_sheets if v.ViewType == view_type_enum]

name_dict = {}
#  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#  !!!!!!!!!!!!!!KEY== Plan Name, VALUE==Plan object!!!!!!!!!!!!
#  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
for x in filtered_views_list:
    name_dict[x.Name] = x

# Display the list of view names for selection
view_names = list(name_dict.keys())  # Get the list of view names

select_view = forms.SelectFromList.show(view_names,
                                multiselect=True,
                                title='Select View',
                                button_name='Select')


# Create a new dictionary to collect plans based on their names in dict
selected_view_dict = {}

# If a selection was made, retrieve the corresponding ViewType and create a new dictionary
for key in select_view:
    if key in name_dict:
        selected_view_dict[key] = name_dict[key]  # Add the selected key-value pair to the new dictionary


# Create a title block for the sheet (use a default title block family type)
title_block = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType().ToElements()

# Create a new dictionary to collect Title Blocks based on their names in dict
tb_dict = {}

# Collecting the names of the title blocks
for tb in title_block:
    tb_dict[tb.FamilyName] = tb

# Display the list of TB names for selection
tb_names = list(tb_dict.keys())  # Get the list of TB names
select_tb = forms.SelectFromList.show(tb_names,
                                multiselect=False,
                                title='Select Title Block',
                                button_name='Select')

tb_value = tb_dict[select_tb]  # This will return value for Key name


paper_type = ["Rolls",
              "A Standart"
             ]

select_paper_type = forms.SelectFromList.show(paper_type,
                                multiselect=False,
                                title='Select Paper Type',
                                button_name='Select Paper Type')


move_drawing_left = forms.ask_for_string(
    default='0',
    prompt='Enter distance for Legend',
    title='Legend Space'
)

distance_to_move = int(move_drawing_left)

move_drawing_up = forms.ask_for_string(
    default='0',
    prompt='Enter distance to Move in Y Axis',
    title='Legend Space'
)

distance_to_move_y = int(move_drawing_up)

# Initialize big_dict with the necessary keys
big_dict = {
    "fits_a": {},
    "fits_rolls": {},
    "bigger_than_rolls": {}
}

t = Transaction(doc, "Turn On Crop Views")
t.Start()
# CHECK DIMMS OF CROP VIEW REGIONS TO DETERMINE SIZE
for key, value in selected_view_dict.items():

    param = value.get_Parameter(BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
    param.Set(1)

    scale = value.Scale
    cb_min, cb_max = size_determiner.get_view_crop_min_max(value)
    # Check if either cb_min or cb_max is None; if so, skip this view
    if cb_min is None or cb_max is None:
        continue
    # Calculate width, depth, and height
    width = abs(cb_max.X - cb_min.X) * 30.48 / scale
    height = abs(cb_max.Y - cb_min.Y) * 30.48 / scale

    if "SD" in select_tb:
        # Variables to determine Sheet Size
        adj_width = width + 10 + distance_to_move  # 10  to accommodate the eventual grids.
        adj_height = height + 10 + distance_to_move_y
    else:
        adj_width = width + 31 + distance_to_move  # 10 is added to the original 21, to accommodate the eventual grids.
        adj_height = height + 10 + distance_to_move_y

    # Distribute Views in "A" and Non "A" lists
    # Determine which category this view belongs to and add it to the appropriate dictionary
    # WIDTH IS LATER USED IN THE FUNCTION TO DETERMINE THE DISTANCE TO MOVE FROM TITLE BLOCK ORIGIN POINT
    if size_determiner.determine_a_size(adj_height, adj_width) != "False":
        # Add to "fits_a" with `value` as key and a dictionary for `width` and `height`
        big_dict["fits_a"][value] = (size_determiner.determine_width(adj_width), adj_height, size_determiner.determine_a_size(adj_height, adj_width), width)

    elif size_determiner.determine_width(adj_width) != 1 and size_determiner.determine_height(adj_height) != 1:
        # Add to "bigger_than_a" with `value` as key and a dictionary for `width` and `height`
        # here we use class for width to get a rounded number to bigger 5
        big_dict["fits_rolls"][value] = (size_determiner.determine_width(adj_width), adj_height, width)

    else:
        # Add to "bigger_than_rolls" with `value` as key and a dictionary for `width` and `height`
        big_dict["bigger_than_rolls"][value] = (adj_width, adj_height, width)

t.Commit()

if size_determiner.views_without_cb:
    cb_message = "{}\n".format(size_determiner.views_without_cb.strip())

    TaskDialog.Show("Views with no Crop Region", cb_message)

sheet_manager = SheetManager(doc, tb_value, big_dict, select_tb, length_display_unit, size_determiner)

# CHOOSE BETWEEN PAPER STANDARDS
if select_paper_type == "A Standart":

    # CREATE SHEETS FOR "FITS_A"
    sheet_manager.process_sheets_fits_a(distance_to_move, distance_to_move_y)

    # Check if there are any items in "bigger_than_rolls" or "fits_rolls"
    if any(big_dict[category] for category in ["bigger_than_rolls", "fits_rolls"]):
        rolls_name_str = ""
        bigger_name_str = ""

        if big_dict["fits_rolls"]:
            for obj in big_dict["fits_rolls"]:
                rolls_name_str += "{}\n".format(obj.Name)
                # Format the final message for the TaskDialog

        if big_dict["bigger_than_rolls"]:
            for obj in big_dict["bigger_than_rolls"]:
                bigger_name_str += "{}\n".format(obj.Name)

        if rolls_name_str and not bigger_name_str:
            message = (
                "{} can fit in rolls.\n"
            ).format(rolls_name_str.strip())

        elif not rolls_name_str and bigger_name_str:
            # Format the final message for the TaskDialog
            message = (
                "{} don't fit in any standard Sheet dimensions!\n"
            ).format(bigger_name_str.strip())
        else:

            # Format the final message for the TaskDialog
            message = (
                "{} can fit in rolls.\n\n"
                "{} don't fit in any standard Sheet dimensions!"
            ).format(rolls_name_str.strip(), bigger_name_str.strip())  # Strip any trailing newlines

        # Show the TaskDialog with the formatted message
        TaskDialog.Show("Fit Check Results", message)

    if any(big_dict["fits_rolls"]):

        paper_type = ["Yes", "No"]

        yes_no = forms.SelectFromList.show(paper_type,
                                           multiselect=False,
                                           title='No A-size title blocks fit.Switch to Rolls?.',
                                           button_name='Select')
        if yes_no == "Yes":

            sheet_manager.process_sheets_fits_rolls(distance_to_move, distance_to_move_y)



if select_paper_type == "Rolls":
    # CREATE SHEETS FOR "FITS_ROLLS"
    sheet_manager.process_sheets_fits_rolls(distance_to_move, distance_to_move_y)

    # CREATE SHEETS FOR "FITS_A"
    for key, value_list in big_dict["fits_a"].items():
        adj_width, adj_height = value_list[0], value_list[1]  # Get width and height from the list

        move = value_list[3]

        # Ensure tb_value and family are defined and accessible
        if tb_value:
            # Retrieve the Family of the selected title block type
            title_block_family = tb_value.Family

            # Collect all types belonging to this family
            family_types = [
                symbol for symbol in title_block
                if symbol.Family.Id == title_block_family.Id
            ]

        for tb_type in family_types:
            name = Element.Name.GetValue(tb_type)
            height_value = tb_type.LookupParameter("Height").AsDouble() * helper.conversion(
                length_display_unit)

            # Check height within tolerance
            tolerance = 0.5
            if abs(height_value - size_determiner.determine_height(adj_height)) < tolerance and not any(
                    substring in name for substring in ["A0", "A1", "A2", "A3"]):
                set_tb = tb_type.Id
                y_move_value = height_value

                sheet_manager.create_sheet(key, set_tb, y_move_value, adj_width, move, distance_to_move, distance_to_move_y)

                break

    # Check if there are any items in "bigger_than_rolls" or "fits_rolls"
    if any(big_dict[category] for category in ["bigger_than_rolls"]):

        bigger_name_str = ""

        if big_dict["bigger_than_rolls"]:
            for obj in big_dict["bigger_than_rolls"]:
                bigger_name_str += "{}\n".format(obj.Name)

        # Format the final message for the TaskDialog
        message = (
            "{} don't fit in any standard Sheet dimensions!"
        ).format(bigger_name_str.strip())  # Strip any trailing newlines

        # Show the TaskDialog with the formatted message
        TaskDialog.Show("Fit Check Results", message)


# Export log file
current_file = __file__.split("\\")
logexporter.logExport(current_file)