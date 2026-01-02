/*
 * Stratus ATC - X-Plane Adapter Plugin
 *
 * This plugin reads X-Plane DataRefs and writes them to a JSON file
 * for consumption by the Stratus ATC native client (Linux/Mac).
 *
 * It also reads commands from the client (via JSONL file) and applies
 * them back to the simulator.
 *
 * Build: See CMakeLists.txt
 * Install: Copy to X-Plane 12/Resources/plugins/StratusATC/
 */

#include "XPLMDataAccess.h"
#include "XPLMPlanes.h"
#include "XPLMPlugin.h"
#include "XPLMProcessing.h"
#include "XPLMUtilities.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

/* Platform-specific includes */
#if IBM
#include <windows.h>
#define PATH_SEP "\\"
#else
#include <pwd.h>
#include <unistd.h>
#define PATH_SEP "/"
#endif

/* Plugin metadata */
#define PLUGIN_NAME "Stratus ATC"
#define PLUGIN_SIG "community.stratus.xplane.atc"
#define PLUGIN_DESC "Bridges X-Plane to Stratus ATC native client"
#define PLUGIN_VERSION "0.2.0"

/* File paths (set at init) */
static char g_data_dir[512] = {0};
static char g_input_file[1024] = {0};  /* We write here (telemetry) */
static char g_output_file[1024] = {0}; /* We read here (commands from client) */
static char g_log_file[1024] = {0};    /* Our own log file */

/* DataRef handles */
static XPLMDataRef dr_lat = NULL;
static XPLMDataRef dr_lon = NULL;
static XPLMDataRef dr_alt_msl = NULL;  /* Altitude MSL in meters */
static XPLMDataRef dr_alt_agl = NULL;  /* Altitude AGL in meters */
static XPLMDataRef dr_hdg_mag = NULL;  /* Magnetic heading */
static XPLMDataRef dr_hdg_true = NULL; /* True heading */
static XPLMDataRef dr_pitch = NULL;
static XPLMDataRef dr_roll = NULL;
static XPLMDataRef dr_gnd_speed = NULL; /* Ground speed m/s */
static XPLMDataRef dr_ias = NULL;       /* Indicated airspeed ktas */
static XPLMDataRef dr_tas = NULL;       /* True airspeed m/s */
static XPLMDataRef dr_vs = NULL;        /* Vertical speed fpm */
static XPLMDataRef dr_on_ground = NULL; /* On ground flag */
static XPLMDataRef dr_paused = NULL;    /* Sim paused */

/* COM/NAV Radios */
static XPLMDataRef dr_com1_freq = NULL;
static XPLMDataRef dr_com1_stdby = NULL;
static XPLMDataRef dr_com2_freq = NULL;
static XPLMDataRef dr_com2_stdby = NULL;
static XPLMDataRef dr_nav1_freq = NULL;
static XPLMDataRef dr_nav2_freq = NULL;

/* Transponder */
static XPLMDataRef dr_xpdr_code = NULL;
static XPLMDataRef dr_xpdr_mode = NULL;

/* Autopilot */
static XPLMDataRef dr_ap_alt = NULL;
static XPLMDataRef dr_ap_hdg = NULL;
static XPLMDataRef dr_ap_vs = NULL;

/* Flight loop callback ID */
static XPLMFlightLoopID g_flight_loop_id = NULL;

/* Logging */
static FILE *g_log_fp = NULL;

/* ============================================================================
 * Logging - writes to our own log file, NOT X-Plane's Log.txt
 * ============================================================================
 */

static void LogOpen(void) {
  if (g_log_fp)
    return;
  g_log_fp = fopen(g_log_file, "a");
  if (g_log_fp) {
    /* Write header on new session */
    time_t now = time(NULL);
    struct tm *tm_info = localtime(&now);
    char time_str[64];
    strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", tm_info);
    fprintf(g_log_fp, "\n=== StratusATC Session Started: %s ===\n",
            time_str);
    fflush(g_log_fp);
  }
}

static void LogClose(void) {
  if (g_log_fp) {
    time_t now = time(NULL);
    struct tm *tm_info = localtime(&now);
    char time_str[64];
    strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", tm_info);
    fprintf(g_log_fp, "=== Session Ended: %s ===\n", time_str);
    fclose(g_log_fp);
    g_log_fp = NULL;
  }
}

static void Log(const char *level, const char *fmt, ...) {
  if (!g_log_fp)
    return;

  /* Timestamp */
  time_t now = time(NULL);
  struct tm *tm_info = localtime(&now);
  char time_str[64];
  strftime(time_str, sizeof(time_str), "%H:%M:%S", tm_info);

  fprintf(g_log_fp, "[%s] [%s] ", time_str, level);

  va_list args;
  va_start(args, fmt);
  vfprintf(g_log_fp, fmt, args);
  va_end(args);

  fprintf(g_log_fp, "\n");
  fflush(g_log_fp);
}

#define LOG_INFO(...) Log("INFO", __VA_ARGS__)
#define LOG_WARN(...) Log("WARN", __VA_ARGS__)
#define LOG_ERROR(...) Log("ERROR", __VA_ARGS__)
#define LOG_DEBUG(...) Log("DEBUG", __VA_ARGS__)

/* Forward declarations */
static float FlightLoopCallback(float inElapsedSinceLastCall,
                                float inElapsedTimeSinceLastFlightLoop,
                                int inCounter, void *inRefcon);
static void InitDataRefs(void);
static void InitFilePaths(void);
static void WriteTelemetryJSON(void);
static void ReadCommandsJSONL(void);

/* ============================================================================
 * Required Plugin Callbacks
 * ============================================================================
 */

PLUGIN_API int XPluginStart(char *outName, char *outSig, char *outDesc) {
  strcpy(outName, PLUGIN_NAME);
  strcpy(outSig, PLUGIN_SIG);
  strcpy(outDesc, PLUGIN_DESC);

  /* Initialize file paths first (needed for log file) */
  InitFilePaths();

  /* Open our log file */
  LogOpen();

  LOG_INFO("Plugin starting (version %s)", PLUGIN_VERSION);
  LOG_INFO("Data directory: %s", g_data_dir);

  InitDataRefs();

  /* Register the flight loop callback at ~1Hz */
  XPLMCreateFlightLoop_t fl_params = {
      .structSize = sizeof(XPLMCreateFlightLoop_t),
      .phase = xplm_FlightLoop_Phase_AfterFlightModel,
      .callbackFunc = FlightLoopCallback,
      .refcon = NULL};
  g_flight_loop_id = XPLMCreateFlightLoop(&fl_params);

  LOG_INFO("Plugin started successfully");
  return 1;
}

PLUGIN_API void XPluginStop(void) {
  if (g_flight_loop_id) {
    XPLMDestroyFlightLoop(g_flight_loop_id);
    g_flight_loop_id = NULL;
  }
  LOG_INFO("Plugin stopped");
  LogClose();
}

PLUGIN_API int XPluginEnable(void) {
  /* Schedule flight loop to run every 1 second */
  if (g_flight_loop_id) {
    XPLMScheduleFlightLoop(g_flight_loop_id, 1.0f, 1);
  }
  LOG_INFO("Plugin enabled - telemetry streaming started");
  return 1;
}

PLUGIN_API void XPluginDisable(void) {
  if (g_flight_loop_id) {
    XPLMScheduleFlightLoop(g_flight_loop_id, 0, 0);
  }
  LOG_INFO("Plugin disabled - telemetry streaming stopped");
}

PLUGIN_API void XPluginReceiveMessage(XPLMPluginID inFromWho, int inMessage,
                                      void *inParam) {
  /* Handle messages from X-Plane or other plugins if needed */
  (void)inFromWho;
  (void)inMessage;
  (void)inParam;
}

/* ============================================================================
 * Implementation
 * ============================================================================
 */

static void InitFilePaths(void) {

#if IBM
  /* Windows: Use %LOCALAPPDATA%\StratusATC */
  const char *localappdata = getenv("LOCALAPPDATA");
  if (localappdata) {
    snprintf(g_data_dir, sizeof(g_data_dir), "%s" PATH_SEP "StratusATC",
             localappdata);
  } else {
    snprintf(g_data_dir, sizeof(g_data_dir), "C:" PATH_SEP "StratusATC");
  }
#elif APL
  /* macOS: Use ~/Library/Application Support/StratusATC */
  const char *home = getenv("HOME");
  if (!home) {
    struct passwd *pw = getpwuid(getuid());
    if (pw)
      home = pw->pw_dir;
  }
  if (home) {
    snprintf(g_data_dir, sizeof(g_data_dir),
             "%s/Library/Application Support/StratusATC", home);
  } else {
    snprintf(g_data_dir, sizeof(g_data_dir), "/tmp/StratusATC");
  }
#else
  /* Linux: Use ~/.local/share/StratusATC */
  const char *home = getenv("HOME");
  if (!home) {
    struct passwd *pw = getpwuid(getuid());
    if (pw)
      home = pw->pw_dir;
  }
  if (home) {
    snprintf(g_data_dir, sizeof(g_data_dir), "%s/.local/share/StratusATC",
             home);
  } else {
    snprintf(g_data_dir, sizeof(g_data_dir), "/tmp/StratusATC");
  }
#endif

  /* Create directory if it doesn't exist */
  struct stat st = {0};
  if (stat(g_data_dir, &st) == -1) {
#if IBM
    CreateDirectoryA(g_data_dir, NULL);
#else
    mkdir(g_data_dir, 0755);
#endif
  }

  snprintf(g_input_file, sizeof(g_input_file),
           "%s" PATH_SEP "simAPI_input.json", g_data_dir);
  snprintf(g_output_file, sizeof(g_output_file),
           "%s" PATH_SEP "simAPI_output.jsonl", g_data_dir);
  snprintf(g_log_file, sizeof(g_log_file),
           "%s" PATH_SEP "stratus_atc.log", g_data_dir);
}

static void InitDataRefs(void) {
  /* Position */
  dr_lat = XPLMFindDataRef("sim/flightmodel/position/latitude");
  dr_lon = XPLMFindDataRef("sim/flightmodel/position/longitude");
  dr_alt_msl = XPLMFindDataRef("sim/flightmodel/position/elevation");
  dr_alt_agl = XPLMFindDataRef("sim/flightmodel/position/y_agl");

  /* Orientation */
  dr_hdg_mag = XPLMFindDataRef("sim/flightmodel/position/mag_psi");
  dr_hdg_true = XPLMFindDataRef("sim/flightmodel/position/true_psi");
  dr_pitch = XPLMFindDataRef("sim/flightmodel/position/theta");
  dr_roll = XPLMFindDataRef("sim/flightmodel/position/phi");

  /* Speed */
  dr_gnd_speed = XPLMFindDataRef("sim/flightmodel/position/groundspeed");
  dr_ias = XPLMFindDataRef("sim/flightmodel/position/indicated_airspeed");
  dr_tas = XPLMFindDataRef("sim/flightmodel/position/true_airspeed");
  dr_vs = XPLMFindDataRef("sim/flightmodel/position/vh_ind_fpm");

  /* State */
  dr_on_ground = XPLMFindDataRef("sim/flightmodel/failures/onground_any");
  dr_paused = XPLMFindDataRef("sim/time/paused");

  /* Radios (Hz values, divide by 10000 for MHz display) */
  dr_com1_freq =
      XPLMFindDataRef("sim/cockpit2/radios/actuators/com1_frequency_hz_833");
  dr_com1_stdby = XPLMFindDataRef(
      "sim/cockpit2/radios/actuators/com1_standby_frequency_hz_833");
  dr_com2_freq =
      XPLMFindDataRef("sim/cockpit2/radios/actuators/com2_frequency_hz_833");
  dr_com2_stdby = XPLMFindDataRef(
      "sim/cockpit2/radios/actuators/com2_standby_frequency_hz_833");
  dr_nav1_freq =
      XPLMFindDataRef("sim/cockpit2/radios/actuators/nav1_frequency_hz");
  dr_nav2_freq =
      XPLMFindDataRef("sim/cockpit2/radios/actuators/nav2_frequency_hz");

  /* Transponder */
  dr_xpdr_code = XPLMFindDataRef("sim/cockpit/radios/transponder_code");
  dr_xpdr_mode = XPLMFindDataRef("sim/cockpit/radios/transponder_mode");

  /* Autopilot */
  dr_ap_alt = XPLMFindDataRef("sim/cockpit/autopilot/altitude");
  dr_ap_hdg = XPLMFindDataRef("sim/cockpit/autopilot/heading_mag");
  dr_ap_vs = XPLMFindDataRef("sim/cockpit/autopilot/vertical_velocity");

  LOG_INFO("DataRefs initialized");
}

static float FlightLoopCallback(float inElapsedSinceLastCall,
                                float inElapsedTimeSinceLastFlightLoop,
                                int inCounter, void *inRefcon) {
  (void)inElapsedSinceLastCall;
  (void)inElapsedTimeSinceLastFlightLoop;
  (void)inCounter;
  (void)inRefcon;

  WriteTelemetryJSON();
  ReadCommandsJSONL();

  return 1.0f; /* Call again in 1 second */
}

static void WriteTelemetryJSON(void) {
  /* Write to temp file first, then rename (atomic) */
  char tmp_file[1024];
  snprintf(tmp_file, sizeof(tmp_file), "%s.tmp", g_input_file);

  FILE *f = fopen(tmp_file, "w");
  if (!f) {
    LOG_ERROR("Failed to open temp file for writing: %s", tmp_file);
    return;
  }

  /* Get current timestamp */
  time_t now = time(NULL);

  /* Read all DataRefs */
  double lat = dr_lat ? XPLMGetDatad(dr_lat) : 0.0;
  double lon = dr_lon ? XPLMGetDatad(dr_lon) : 0.0;
  double alt_msl = dr_alt_msl ? XPLMGetDatad(dr_alt_msl) : 0.0;
  float alt_agl = dr_alt_agl ? XPLMGetDataf(dr_alt_agl) : 0.0f;
  float hdg_mag = dr_hdg_mag ? XPLMGetDataf(dr_hdg_mag) : 0.0f;
  float hdg_true = dr_hdg_true ? XPLMGetDataf(dr_hdg_true) : 0.0f;
  float pitch = dr_pitch ? XPLMGetDataf(dr_pitch) : 0.0f;
  float roll = dr_roll ? XPLMGetDataf(dr_roll) : 0.0f;
  float gnd_spd = dr_gnd_speed ? XPLMGetDataf(dr_gnd_speed) : 0.0f;
  float ias = dr_ias ? XPLMGetDataf(dr_ias) : 0.0f;
  float tas = dr_tas ? XPLMGetDataf(dr_tas) : 0.0f;
  float vs = dr_vs ? XPLMGetDataf(dr_vs) : 0.0f;
  int on_gnd = dr_on_ground ? XPLMGetDatai(dr_on_ground) : 0;
  int paused = dr_paused ? XPLMGetDatai(dr_paused) : 0;

  int com1 = dr_com1_freq ? XPLMGetDatai(dr_com1_freq) : 0;
  int com1_sb = dr_com1_stdby ? XPLMGetDatai(dr_com1_stdby) : 0;
  int com2 = dr_com2_freq ? XPLMGetDatai(dr_com2_freq) : 0;
  int com2_sb = dr_com2_stdby ? XPLMGetDatai(dr_com2_stdby) : 0;
  int nav1 = dr_nav1_freq ? XPLMGetDatai(dr_nav1_freq) : 0;
  int nav2 = dr_nav2_freq ? XPLMGetDatai(dr_nav2_freq) : 0;
  int xpdr = dr_xpdr_code ? XPLMGetDatai(dr_xpdr_code) : 0;
  int xpdr_mode = dr_xpdr_mode ? XPLMGetDatai(dr_xpdr_mode) : 0;

  float ap_alt = dr_ap_alt ? XPLMGetDataf(dr_ap_alt) : 0.0f;
  float ap_hdg = dr_ap_hdg ? XPLMGetDataf(dr_ap_hdg) : 0.0f;
  float ap_vs = dr_ap_vs ? XPLMGetDataf(dr_ap_vs) : 0.0f;

  /* Get aircraft info */
  char acf_path[512] = {0};
  char acf_file[256] = {0};
  XPLMGetNthAircraftModel(0, acf_file, acf_path);

  /* Write JSON (manual formatting to avoid external deps) */
  fprintf(f, "{\n");
  fprintf(f, "  \"timestamp\": %ld,\n", (long)now);
  fprintf(f, "  \"simulator\": \"X-Plane\",\n");
  fprintf(f, "  \"aircraft\": \"%s\",\n", acf_file);
  fprintf(f, "  \"position\": {\n");
  fprintf(f, "    \"latitude\": %.8f,\n", lat);
  fprintf(f, "    \"longitude\": %.8f,\n", lon);
  fprintf(f, "    \"altitude_msl_m\": %.2f,\n", alt_msl);
  fprintf(f, "    \"altitude_agl_m\": %.2f\n", alt_agl);
  fprintf(f, "  },\n");
  fprintf(f, "  \"orientation\": {\n");
  fprintf(f, "    \"heading_mag\": %.2f,\n", hdg_mag);
  fprintf(f, "    \"heading_true\": %.2f,\n", hdg_true);
  fprintf(f, "    \"pitch\": %.2f,\n", pitch);
  fprintf(f, "    \"roll\": %.2f\n", roll);
  fprintf(f, "  },\n");
  fprintf(f, "  \"speed\": {\n");
  fprintf(f, "    \"ground_speed_mps\": %.2f,\n", gnd_spd);
  fprintf(f, "    \"ias_kts\": %.2f,\n", ias);
  fprintf(f, "    \"tas_mps\": %.2f,\n", tas);
  fprintf(f, "    \"vertical_speed_fpm\": %.2f\n", vs);
  fprintf(f, "  },\n");
  fprintf(f, "  \"radios\": {\n");
  fprintf(f, "    \"com1_hz\": %d,\n", com1);
  fprintf(f, "    \"com1_standby_hz\": %d,\n", com1_sb);
  fprintf(f, "    \"com2_hz\": %d,\n", com2);
  fprintf(f, "    \"com2_standby_hz\": %d,\n", com2_sb);
  fprintf(f, "    \"nav1_hz\": %d,\n", nav1);
  fprintf(f, "    \"nav2_hz\": %d\n", nav2);
  fprintf(f, "  },\n");
  fprintf(f, "  \"transponder\": {\n");
  fprintf(f, "    \"code\": %d,\n", xpdr);
  fprintf(f, "    \"mode\": %d\n", xpdr_mode);
  fprintf(f, "  },\n");
  fprintf(f, "  \"autopilot\": {\n");
  fprintf(f, "    \"altitude_ft\": %.0f,\n", ap_alt);
  fprintf(f, "    \"heading\": %.0f,\n", ap_hdg);
  fprintf(f, "    \"vs_fpm\": %.0f\n", ap_vs);
  fprintf(f, "  },\n");
  fprintf(f, "  \"state\": {\n");
  fprintf(f, "    \"on_ground\": %s,\n", on_gnd ? "true" : "false");
  fprintf(f, "    \"paused\": %s\n", paused ? "true" : "false");
  fprintf(f, "  }\n");
  fprintf(f, "}\n");

  fclose(f);

  /* Atomic rename */
  rename(tmp_file, g_input_file);
}

static void ReadCommandsJSONL(void) {
  /* TODO: Implement command reading from simAPI_output.jsonl */
  /*
   * Commands from the client would include:
   * - set_com1_frequency
   * - set_transponder_code
   * - set_autopilot_altitude
   * etc.
   *
   * Each line is a JSON object. We read, parse, execute, then truncate.
   */
}
