from app.services.query_parser import parse_query
def test_full_query():
    q=parse_query("Find a man in a dark green hoodie with a backpack walking")
    assert q.gender == "male" and q.upper_type == "hoodie" and q.upper_color == "dark_green" and q.accessories == ["backpack"] and q.action == "walk"
def test_synonyms_and_objects():
    assert parse_query("woman in pink top with rucksack").gender == "female"
    assert "backpack" in parse_query("woman in pink top with rucksack").accessories
    assert parse_query("person holding a phone").objects_held == ["phone"]
def test_relationship_query_is_structured():
    q=parse_query("Find a man carrying a dog")
    assert q.gender == "male" and q.object_class == "dog" and q.relationship == "carrying"
def test_standalone_object_query():
    q=parse_query("find a dog")
    assert q.subject_class == "object" and q.object_class == "dog"

def test_lower_clothing_colour():
    q=parse_query("Find people wearing black lower clothing")
    assert q.lower_color == "black" and q.upper_color is None

def test_gender_plural():
    assert parse_query("How many women are in the video?").gender == "female"
