#!/bin/sh

XRES=1920
YRES=1080

AXIS_BROADCAST="axi:axis_broadcasteraxis_broadc"
DISPLAY_TPG="a00a0000.v_tpg"
RECORD_TPG="a00d0000.v_tpg"
PIPELINE_FMT="UYVY8_1X16/${XRES}x${YRES}"

DISPLAY_DEV="/dev/video0"
RECORD_DEV="/dev/video1"

GST_CAP_CAPS="video/x-raw, width=${XRES}, height=${YRES}, format=YUY2"
GST_REC_CAPS="video/x-raw, width=${XRES}, height=${YRES}, format=NV16"

GST_KMSSINK_DP="kmssink plane-id=39"
GST_KMSSSINK_SDI="\
kmssink connector-id=38 bus-id=axi:drm-pl-disp-drvSDI_Sink_1_v_smpte_uhdsdi_tx_ss_0 \
connector-properties=\"props,sdi_mode=2,sdi_data_stream=2,is_frac=0\" show-preroll-frame=false \
force-modesetting=true"

GST_REC_PIPE="omxh264enc ! h264parse ! mp4mux ! filesink"

# AXI GPIO used to control TREADY lines
# 0x02 = Display Only
# 0x01 = Record Only
# 0x00 = Display & Record
MULT_SINK_SEL_ADDR="0xa00e0000"

# Stop any processes gracefully when script is closed
trap 'kill -s STOP $(jobs -p)' INT

configure_default_pipeline() {
    # Setup pipeline streaming format
    # Broadcast
    media-ctl -V "'${AXIS_BROADCAST}':0 [fmt:${PIPELINE_FMT} field:none]"

    # Display pipeline
    media-ctl -V "\
    '${DISPLAY_TPG}':0 [fmt:${PIPELINE_FMT} field:none], \
    'a0020000.v_proc_ss':0 [fmt:${PIPELINE_FMT} field:none]\
    "

    # Record pipeline
    media-ctl -V "'${RECORD_TPG}':0 [fmt:${PIPELINE_FMT} field:none]"

    # Set Display TPG display to pass through video input
    v4l2-ctl -d $(media-ctl -e ${DISPLAY_TPG}) --set-ctrl test_pattern=0
    v4l2-ctl -d $(media-ctl -e ${RECORD_TPG}) --set-ctrl test_pattern=0
}

configure_display() {
    configure_default_pipeline
    devmem ${MULT_SINK_SEL_ADDR} 32 0x02
}

configure_record() {
    configure_default_pipeline
    devmem ${MULT_SINK_SEL_ADDR} 32 0x01
}

configure_display_record() {
    configure_default_pipeline
    devmem ${MULT_SINK_SEL_ADDR} 32 0x00
}

display_dp() {
    configure_display

    # Set global alpha on RGB plane to 0
    modetest -M xlnx -w 41:alpha:0

    # Start modetest to set mode of main RGB plane to desired resolution
    modetest -M xlnx -s 45:${XRES}x${YRES}@AR24 &

    # Launch video pipeline
    gst-launch-1.0 v4l2src device=${DISPLAY_DEV} ! ${GST_CAP_CAPS} ! ${GST_KMSSINK_DP} &
}

display_sdi() {
    configure_display

    # An initial modeset is needed to get video to display, otherwise it only works on the second try
    gst-launch-1.0 v4l2src num-buffers=0 device=${DISPLAY_DEV} ! ${GST_CAP_CAPS} ! ${GST_KMSSSINK_SDI}

    gst-launch-1.0 v4l2src device=${DISPLAY_DEV} ! ${GST_CAP_CAPS} ! ${GST_KMSSSINK_SDI} &
}

display_dual() {
    configure_display_record

    # DP
    # Set global alpha on RGB plane to 0
    modetest -M xlnx -w 41:alpha:0

    # Start modetest to set mode of main RGB plane to desired resolution
    modetest -M xlnx -s 45:${XRES}x${YRES}@AR24 &

    # Launch video pipeline
    gst-launch-1.0 v4l2src device=${DISPLAY_DEV} ! ${GST_CAP_CAPS} ! ${GST_KMSSINK_DP} &

    # SDI
    # An initial modeset is needed to get video to display, otherwise it only works on the second try
    gst-launch-1.0 v4l2src num-buffers=0 device=${RECORD_DEV} ! ${GST_CAP_CAPS} ! ${GST_KMSSSINK_SDI}

    gst-launch-1.0 v4l2src device=${RECORD_DEV} ! ${GST_CAP_CAPS} ! ${GST_KMSSSINK_SDI} &
}

record_video() {
    location=${1}
    skip_configure=${2}

    if [[ ! -n "${skip_configure}" ]]; then
      configure_record
    fi

    gst-launch-1.0 v4l2src device=${RECORD_DEV} ! ${GST_REC_CAPS} ! ${GST_REC_PIPE} location=${location} -e &
}

# Set default values
display=""
record=""
configure=""

# Function to display help message
display_help() {
  echo "Usage: $0 [options]"
  echo ""
  echo "Options:"
  echo "  --configure <mode>  Configure pipeline for display, record, or display-record mode"
  echo "  --display <display>  Display output to specified display (dp or sdi)"
  echo "  --display-dual      Display output to DP and SDI at the same time, Cannot be used with --record."
  echo "  --record <file>     Record output to specified file"
  echo "  --help              Display this help message"
  echo ""
  echo "Examples:"
  echo "  $0 --configure display"
  echo "  $0 --display sdi"
  echo "  $0 --record output.mp4"
  echo "  $0 --display dp --record output.mp4"
  echo "  $0 --display-dual"
  echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --configure)
      if [[ -z "$2" ]]; then
        echo "Error: --configure requires a mode argument (display, record, or display-record)"
        display_help
        exit 1
      fi
      configure="$2"
      shift 2
      ;;
    --display)
      if [[ -z "$2" ]]; then
        echo "Error: --display requires a display argument (dp or sdi)"
        display_help
        exit 1
      fi
      display="$2"
      shift 2
      ;;
    --record)
      if [[ -z "$2" ]]; then
        echo "Error: --record requires a filename argument"
        display_help
        exit 1
      fi
      record="$2"
      shift 2
      ;;
    --display-dual)
      display_dual_flag=true
      shift
      ;;
    --help)
      display_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      display_help
      exit 1
      ;;
  esac
done

# Check for incompatible options
if [[ "$display_dual_flag" == true && -n "$record" ]]; then
  echo "Error: --display-dual cannot be used with --record."
  display_help
  exit 1
fi

# Check if configure mode is set
if [[ -n "$configure" ]]; then
  # Call your configure function here based on the value of $configure
  case "$configure" in
    display)
      # Configure for display mode
      configure_display
      exit 0
      ;;
    record)
      # Configure for record mode
      configure_record
      exit 0
      ;;
    display-record)
      # Configure for display and record mode
      configure_display_record
      exit 0
      ;;
    *)
      echo "Invalid configure mode: $configure"
      display_help
      exit 1
      ;;
  esac
  exit 0
fi

# Check if display and/or record options are set
if [[ "$display_dual_flag" == true ]]; then
    display_dual
    echo dual mode
elif [[ -n "$display" ]]; then
  echo display!!!!!!!!!!!!!!!!!!!!!
  # Call your display function here based on the value of $display
  case "$display" in
    dp)
      # Display to DisplayPort
      display_dp
      ;;
    sdi)
      # Display to SDI
      display_sdi
      ;;
    *)
      echo "Invalid display option: $display"
      display_help
      exit 1
      ;;
  esac
fi

if [[ -n "$record" ]]; then
  if [[ -n "$display" ]]; then
    configure_display_record
    record_video "$record" true
  else
    record_video "$record"
  fi
fi

# If no options are provided, default to displaying to DisplayPort
if [[ -z "$display" && -z "$record" && -z "$configure" && -z "$display_dual_flag" ]]; then
  display_dp
fi

# Anything here has a forking process so wait for control c
wait
