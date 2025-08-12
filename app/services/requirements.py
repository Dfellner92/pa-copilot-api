_CODE_RULES = {
    "70551": {"requires": True, "docs": ["Clinical notes", "Recent imaging"]},  # MRI brain wo contrast
    "70553": {"requires": True, "docs": ["Clinical notes", "Neurology consult", "Previous MRI"]},
    "97110": {"requires": False, "docs": []},  # Therapeutic exercises
}

# Return whether prior auth is required and a list of required documents.
def check_requirements(code: str) -> tuple[bool, list[str]]:   
    rule = _CODE_RULES.get(code)
    if not rule:
        return True, ["Clinical notes"]
    return rule["requires"], rule["docs"]