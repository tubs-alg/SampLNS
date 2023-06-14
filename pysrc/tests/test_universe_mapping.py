from samplns.universe_mapping import UniverseMapping

def test_trivial():
    um = UniverseMapping()
    um.map("old_a", "new_b")
    assert um.to_origin_universe({"new_b": True}) == {"old_a": True}

def test_2():
    um = UniverseMapping()
    um.map("old_a", "new_a")
    um.map("old_b", "new_a")
    assert um.to_origin_universe({"new_a": True}) == {"old_a": True, "old_b": True}


def test_3():
    um = UniverseMapping()
    um.map("old_a", "new_a")
    um.map("old_b", "new_a", inverse=True)
    assert um.to_origin_universe({"new_a": True}) == {"old_a": True, "old_b": False}
    
