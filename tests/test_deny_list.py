from app.llm.deny_list import find_deny_violations


def test_catches_seafood_beef_pork():
    names = ["Chicken thighs", "Beef mince", "Salmon fillets", "Bacon", "Rice"]
    assert set(find_deny_violations(names)) == {"Beef mince", "Salmon fillets", "Bacon"}


def test_case_insensitive_and_substring():
    assert find_deny_violations(["SHRIMP paste", "tinned Tuna"]) == ["SHRIMP paste", "tinned Tuna"]


def test_clean_list_has_no_violations():
    names = ["Chicken thighs", "Paneer", "Tofu", "Rice", "Spinach", "Eggs"]
    assert find_deny_violations(names) == []


def test_does_not_false_positive_on_unrelated_substrings():
    # "hamburger bun" and "codependent"-style substring traps
    assert find_deny_violations(["Hamburger buns", "Codebreaker snacks"]) == []
