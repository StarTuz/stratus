cmake_minimum_required(VERSION 3.16)
project(StratusATC VERSION 0.2.0 LANGUAGES C)

# ============================================================================
# X-Plane SDK Configuration
# ============================================================================
# You need to download the X-Plane SDK from:
# https://developer.x-plane.com/sdk/plugin-sdk-downloads/
# Extract to: adapters/xplane/sdk/
# Expected structure:
#   sdk/CHeaders/XPLM/
#   sdk/CHeaders/Widgets/
#   sdk/CHeaders/Wrappers/
#   sdk/Libraries/Win/
#   sdk/Libraries/Mac/

set(XPLANE_SDK_PATH "${CMAKE_CURRENT_SOURCE_DIR}/sdk" CACHE PATH "Path to X-Plane SDK")

# Verify SDK exists
if(NOT EXISTS "${XPLANE_SDK_PATH}/CHeaders/XPLM/XPLMPlugin.h")
    message(FATAL_ERROR 
        "X-Plane SDK not found at ${XPLANE_SDK_PATH}\n"
        "Download from: https://developer.x-plane.com/sdk/plugin-sdk-downloads/\n"
        "Extract to: ${CMAKE_CURRENT_SOURCE_DIR}/sdk/")
endif()

# ============================================================================
# Platform Detection
# ============================================================================
if(WIN32)
    set(XPLANE_PLATFORM "win")
    set(XPLANE_PLATFORM_DEFINE "IBM=1" "XPLM200=1" "XPLM210=1" "XPLM300=1" "XPLM301=1")
elseif(APPLE)
    set(XPLANE_PLATFORM "mac")
    set(XPLANE_PLATFORM_DEFINE "APL=1" "XPLM200=1" "XPLM210=1" "XPLM300=1" "XPLM301=1")
else()
    set(XPLANE_PLATFORM "lin")
    set(XPLANE_PLATFORM_DEFINE "LIN=1" "XPLM200=1" "XPLM210=1" "XPLM300=1" "XPLM301=1")
endif()

# 64-bit only (X-Plane 11+ requirement)
set(XPLANE_ARCH "x64")

message(STATUS "Building for: ${XPLANE_PLATFORM}_${XPLANE_ARCH}")

# ============================================================================
# Plugin Target
# ============================================================================
add_library(stratus_plugin SHARED
    src/stratus_plugin.c
)

# Include SDK headers
target_include_directories(stratus_plugin PRIVATE
    ${XPLANE_SDK_PATH}/CHeaders/XPLM
    ${XPLANE_SDK_PATH}/CHeaders/Widgets
    ${XPLANE_SDK_PATH}/CHeaders/Wrappers
)

# Platform defines
target_compile_definitions(stratus_plugin PRIVATE
    ${XPLANE_PLATFORM_DEFINE}
)

# ============================================================================
# Platform-Specific Linking
# ============================================================================
if(WIN32)
    # Windows: Link against XPLM_64.lib
    target_link_libraries(stratus_plugin PRIVATE
        ${XPLANE_SDK_PATH}/Libraries/Win/XPLM_64.lib
    )
    # Output name: StratusATC.xpl
    set_target_properties(stratus_plugin PROPERTIES
        OUTPUT_NAME "StratusATC"
        SUFFIX ".xpl"
        PREFIX ""
    )

elseif(APPLE)
    # macOS: Link against XPLM.framework
    find_library(XPLM_FRAMEWORK XPLM PATHS ${XPLANE_SDK_PATH}/Libraries/Mac)
    target_link_libraries(stratus_plugin PRIVATE
        ${XPLM_FRAMEWORK}
        "-framework CoreFoundation"
    )
    set_target_properties(stratus_plugin PROPERTIES
        OUTPUT_NAME "StratusATC"
        SUFFIX ".xpl"
        PREFIX ""
        BUNDLE FALSE
    )

else()
    # Linux: No link libraries, use linker flags
    target_link_options(stratus_plugin PRIVATE
        -shared
        -rdynamic
        -nodefaultlibs
        -Wl,--version-script=${CMAKE_CURRENT_SOURCE_DIR}/exports.txt
    )
    # Link standard C library
    target_link_libraries(stratus_plugin PRIVATE
        c
        m
    )
    set_target_properties(stratus_plugin PROPERTIES
        OUTPUT_NAME "StratusATC"
        SUFFIX ".xpl"
        PREFIX ""
    )
endif()

# ============================================================================
# Output Directory Structure (Fat Plugin 3.0 format)
# ============================================================================
# Creates: StratusATC/lin_x64/StratusATC.xpl
#          StratusATC/mac_x64/StratusATC.xpl
#          StratusATC/win_x64/StratusATC.xpl

set(PLUGIN_OUTPUT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/StratusATC/${XPLANE_PLATFORM}_${XPLANE_ARCH}")

set_target_properties(stratus_plugin PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${PLUGIN_OUTPUT_DIR}"
    RUNTIME_OUTPUT_DIRECTORY "${PLUGIN_OUTPUT_DIR}"
)

# ============================================================================
# Installation
# ============================================================================
# Optional: Install to a custom X-Plane plugins directory
# cmake -DXPLANE_PLUGIN_DIR=/path/to/X-Plane/Resources/plugins ..

if(DEFINED XPLANE_PLUGIN_DIR)
    install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/StratusATC"
            DESTINATION "${XPLANE_PLUGIN_DIR}"
            FILES_MATCHING PATTERN "*.xpl")
endif()

message(STATUS "Plugin will be built to: ${PLUGIN_OUTPUT_DIR}")
