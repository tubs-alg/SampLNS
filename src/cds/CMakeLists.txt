add_library(cds)

# target_link_libraries(cds -static)
target_link_libraries(cds gurobi::gurobi nlohmann_json::nlohmann_json fmt)

# set_target_properties(cds PROPERTIES LINK_SEARCH_START_STATIC 1)
# set_target_properties(cds PROPERTIES LINK_SEARCH_END_STATIC 1)

target_include_directories(cds PUBLIC ../../include)
target_sources(cds
        PUBLIC
        ../../include/cds/cds.hpp
        ../../include/cds/cds_lns.hpp
        ../../include/cds/cds_ip.hpp
        ../../include/cds/cds_heuristic.hpp
        ../../include/cds/cds_genetic.hpp
        ../../include/mis/mis_ip.hpp
        ../../include/graph.hpp
        ../../include/instance.hpp
        ../../include/lns.hpp
        ../../include/parser.hpp
        PRIVATE
        ./cds.cpp)
