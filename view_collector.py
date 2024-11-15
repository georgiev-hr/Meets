from Autodesk.Revit.DB import *

class ViewCollector:
    def __init__(self, doc):
        self.doc = doc

    # Collect All Views
    def get_all_views(self):
        return FilteredElementCollector(self.doc).OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()

    # Collect Phases
    def get_unique_phases(self):
        phases = set()
        dummy_phases = {"00-WIP", None, "", " "}
        for view in self.get_all_views():
            phase_param = view.LookupParameter("Phasing")
            if phase_param:
                phase_value = phase_param.AsString()
                if phase_value not in dummy_phases:
                    phases.add(phase_value)
        return sorted(phases)

    def filter_views_by_phase(self, phase):
        regular_views = []
        for v in self.get_all_views():
            phase_param = v.LookupParameter("Phasing")
            view_name_param = v.get_Parameter(BuiltInParameter.VIEW_NAME)

            if phase_param and phase_param.AsString() == phase:
                if "Delete" not in view_name_param.AsString() or v.ViewType == ViewType.Schedule:
                    regular_views.append(v)
        return regular_views

    def filter_views_not_on_sheets(self, views):
        viewports = FilteredElementCollector(self.doc).OfClass(Viewport).WhereElementIsNotElementType().ToElements()
        view_ids_on_sheets = {vp.ViewId for vp in viewports}
        return [view for view in views if view.Id not in view_ids_on_sheets]