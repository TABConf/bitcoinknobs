cmake_minimum_required(VERSION 3.22)

project(BitcoinKnobsQmlWrapper LANGUAGES NONE)

set(GUI_QML_SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/gui-qml)

set(BITCOIN_KNOBS_QML_PATCHSET_DIR ${CMAKE_CURRENT_SOURCE_DIR}/patches)

file(GLOB _patch_files ${BITCOIN_KNOBS_QML_PATCHSET_DIR}/*.patch)
foreach(_patch_file IN LISTS _patch_files)
  execute_process(
    COMMAND git -C ${GUI_QML_SOURCE_DIR} apply --check ${_patch_file}
    RESULT_VARIABLE _check_result
    OUTPUT_VARIABLE _check_stdout
    ERROR_VARIABLE _check_stderr
  )
  if(NOT _check_result EQUAL 0)
    message(FATAL_ERROR "Failed to apply ${_patch_file}: ${_check_stdout}${_check_stderr}")
  endif()
  execute_process(
    COMMAND git -C ${GUI_QML_SOURCE_DIR} apply ${_patch_file}
    RESULT_VARIABLE _apply_result
    OUTPUT_VARIABLE _apply_stdout
    ERROR_VARIABLE _apply_stderr
  )
  if(NOT _apply_result EQUAL 0)
    message(FATAL_ERROR "Failed to apply ${_patch_file}: ${_apply_stdout}${_apply_stderr}")
  endif()
endforeach()

if(NOT EXISTS ${GUI_QML_SOURCE_DIR}/CMakeLists.txt)
  message(FATAL_ERROR "gui-qml submodule not found. Run 'git submodule update --init --recursive'.")
endif()

set(BITCOIN_KNOBS_QML_BINARY_DIR ${CMAKE_BINARY_DIR}/gui-qml)

add_subdirectory(${GUI_QML_SOURCE_DIR} ${BITCOIN_KNOBS_QML_BINARY_DIR})

set(_knobs_executable bitcoin-core-app)
if(TARGET ${_knobs_executable})
  set_target_properties(${_knobs_executable} PROPERTIES OUTPUT_NAME "bitcoin-knobs")
endif()

