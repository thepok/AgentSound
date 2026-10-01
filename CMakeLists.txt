cmake_minimum_required(VERSION 3.24)
project(AgentSound LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(AGENTSOUND_BUILD_TESTS "Build deterministic engine tests" ON)

# Static runtime so the exe runs without MinGW DLLs on PATH.
if(MINGW)
    add_link_options(-static -static-libgcc -static-libstdc++)
endif()

# Vendored DX7 core (Apache-2.0, see third_party/msfa/PROVENANCE.json).
file(GLOB MSFA_SOURCES CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/third_party/msfa/*.cc)
add_library(msfa STATIC ${MSFA_SOURCES})
target_include_directories(msfa PUBLIC ${CMAKE_SOURCE_DIR}/third_party/msfa)
target_compile_options(msfa PRIVATE -w)

# Engine library: every .cpp under engine/ except the CLI entry point.
file(GLOB_RECURSE ENGINE_SOURCES CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/engine/*.cpp)
list(FILTER ENGINE_SOURCES EXCLUDE REGEX ".*/engine/main\\.cpp$")
add_library(agentsound_engine STATIC ${ENGINE_SOURCES})
target_include_directories(agentsound_engine PUBLIC
    ${CMAKE_SOURCE_DIR}/engine
    ${CMAKE_SOURCE_DIR}/third_party)
target_link_libraries(agentsound_engine PUBLIC msfa)
target_compile_options(agentsound_engine PRIVATE -Wall -Wextra -Wno-unused-parameter)

if(EXISTS ${CMAKE_SOURCE_DIR}/engine/main.cpp)
    add_executable(agentsound ${CMAKE_SOURCE_DIR}/engine/main.cpp)
    target_link_libraries(agentsound PRIVATE agentsound_engine)
endif()

if(AGENTSOUND_BUILD_TESTS)
    enable_testing()
    # One executable per tests/test_*.cpp; each returns nonzero on failure.
    file(GLOB TEST_SOURCES CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/tests/test_*.cpp)
    foreach(test_source ${TEST_SOURCES})
        get_filename_component(test_name ${test_source} NAME_WE)
        add_executable(${test_name} ${test_source})
        target_link_libraries(${test_name} PRIVATE agentsound_engine)
        add_test(NAME ${test_name} COMMAND ${test_name}
                 WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
    endforeach()
endif()
