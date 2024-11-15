# size_determiner.py
from Autodesk.Revit.DB import XYZ
from Autodesk.Revit.UI import TaskDialog

class SizeDeterminer:
    def __init__(self, length_display_unit):
        self.length_display_unit = length_display_unit
        self.views_without_cb = ""
    def get_view_crop_min_max(self, view):
        # Ensure the crop box is active (cropping is enabled for the view)
        if not view.CropBoxActive:
            self.views_without_cb += "{}\n".format(view.Name)
            #TaskDialog.Show("Warning", "Crop Region is not active for this view: {}".format(view.Name))
            return None, None

        # Try to get the CropRegionShapeManager for the view
        crop_manager = view.GetCropRegionShapeManager()

        try:
            # Retrieve the crop shape curves
            crop_curves = crop_manager.GetCropShape()

            # Check if there's only one rectangular boundary curve
            if len(crop_curves) == 1:
                # If there's a single rectangular boundary, use the CropBox min and max
                crop_box = view.CropBox
                return crop_box.Min, crop_box.Max
            else:
                # If more than one curve is present, treat it as an irregular shape
                min_point = None
                max_point = None

                # Loop through all the curves to determine min and max extents
                for curve in crop_curves:
                    curve_min = curve.GetEndPoint(0)
                    curve_max = curve.GetEndPoint(1)

                    if min_point is None or max_point is None:
                        # Initialize with the first curve's points
                        min_point = XYZ(min(curve_min.X, curve_max.X), min(curve_min.Y, curve_max.Y), 0)
                        max_point = XYZ(max(curve_min.X, curve_max.X), max(curve_min.Y, curve_max.Y), 0)
                    else:
                        # Update min and max points
                        min_point = XYZ(min(min_point.X, curve_min.X, curve_max.X),
                                        min(min_point.Y, curve_min.Y, curve_max.Y), 0)
                        max_point = XYZ(max(max_point.X, curve_min.X, curve_max.X),
                                        max(max_point.Y, curve_min.Y, curve_max.Y), 0)
                return min_point, max_point

        except Exception as e:
            TaskDialog.Show("Error retrieving crop shape:", e)
            return None, None

    def determine_height(self, value):
        # Determine the fit category based on width
        if value < 29.7:
            return 29.7
        elif 29.7 <= value < 42:
            return 42
        elif 42 <= value < 62:
            return 62
        elif 62 <= value < 91.4:
            return 91.4
        elif 91.4 <= value < 106.7:
            return 106.7
            # elif 106.7 <= value < 118.8:
            return 118.8
            # elif 118.8 <= value < 152:
            return 152
        else:
            # return TaskDialog.Show("Warning", "You have exceeded the maximum height for printing rolls available!Please reduce Crop Region!")
            return 1

    def determine_a_size(self, h, w):
        # Determine the fit category based on width
        if h < 42 and w < 29.7:
            return "A3"
        elif h < 42 and w < 59.4:
            return "A2"
        elif h < 59.4 and w < 84.1:
            return "A1"
        elif h < 84.1 and w < 118.9:
            return "A0"
        else:
            return "False"

    def determine_width(self, target_value):
        # Create the set with values from 25 to 300 with a step of 5
        my_set = set(range(25, 301, 5))

        # Return False if target_value is greater than 301
        if target_value > 301:
            return 1

        closest_larger_value = None

        for value in my_set:
            if value > target_value:
                if closest_larger_value is None or value < closest_larger_value:
                    closest_larger_value = value

        return closest_larger_value