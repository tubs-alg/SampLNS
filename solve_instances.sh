#!/bin/bash
#
# SampLNS Instance Solver Script
# ==============================
#
# This script processes all .xml and .dimacs instance files in the ./instances/ directory
# and generates corresponding output files in the ./results/ directory using a Docker container.
#
# Prerequisites:
# - Docker container built with: docker build --platform linux/amd64 -t samplns .
# - Instance files in XML (FeatJAR) or DIMACS (.dimacs) format
#
# Usage:
#   ./solve_instances.sh [OPTIONS]
#
# # Use defaults (original behavior)
# ./solve_instances.sh
# # Custom directories
# ./solve_instances.sh -i ./my_instances -o ./my_results
# # Different time limit
# ./solve_instances.sh --samplns-timelimit 7200
# # Custom Docker image
# ./solve_instances.sh --docker samplns:v2.0
# # Multiple options
# ./solve_instances.sh -i ./data --initial-sample-algorithm YASA5 --samplns-max-iterations 100
# # Custom sleep duration
# ./solve_instances.sh --sleep 10
# # Help
# ./solve_instances.sh --help

set -euo pipefail # Exit on error, undefined vars, pipe failures

# Default configuration
INSTANCE_FOLDER="./instances"
RESULTS_FOLDER="./results"
GUROBI_LICENSE="./gurobi.lic"
INITIAL_SAMPLE_ALGORITHM="YASA"
INITIAL_SAMPLE_ALGORITHM_TIMELIMIT="3600"
SAMPLNS_TIMELIMIT="3600"
SAMPLNS_MAX_ITERATIONS=""
SAMPLNS_ITERATION_TIMELIMIT=""
CDS_ITERATION_TIMELIMIT=""
INITIAL_SAMPLE=""
DOCKER_IMAGE="samplns"
DOCKER_PLATFORM="linux/amd64"
SLEEP_DURATION=5

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Process .xml and .dimcas instance files using SampLNS solver in Docker.

OPTIONS:
    -i, --instances DIR                    Instance directory (default: $INSTANCE_FOLDER)
    -o, --output DIR                       Results directory (default: $RESULTS_FOLDER)
    -l, --license FILE                     Gurobi license file (default: $GUROBI_LICENSE)
    -d, --docker IMAGE                     Docker image name (default: $DOCKER_IMAGE)
    -p, --platform PLATFORM               Docker platform (default: $DOCKER_PLATFORM)
    -s, --sleep SEC                        Sleep duration after each solve (default: $SLEEP_DURATION)
    --initial-sample FILE                  Path to initial sample JSON file
    --initial-sample-algorithm ALG         Initial sampling algorithm: YASA, YASA3, YASA5, YASA10 (default: $INITIAL_SAMPLE_ALGORITHM)
    --initial-sample-algorithm-timelimit SEC  Timelimit for initial sampling (default: $INITIAL_SAMPLE_ALGORITHM_TIMELIMIT)
    --samplns-timelimit SEC                SampLNS timelimit in seconds (default: $SAMPLNS_TIMELIMIT)
    --samplns-max-iterations NUM           Maximum SampLNS iterations
    --samplns-iteration-timelimit SEC      SampLNS iteration timelimit in seconds
    --cds-iteration-timelimit SEC          CDS iteration timelimit in seconds
    -h, --help                             Show this help message

EXAMPLES:
    $0                                                    # Use defaults
    $0 -i ./my_instances -o ./my_results                  # Custom directories
    $0 --initial-sample-algorithm YASA5 --samplns-timelimit 1800    # Custom algorithm and time
    $0 --initial-sample ./sample.json                    # Use existing sample
    $0 --samplns-max-iterations 50 --sleep 10           # Custom iterations and sleep
EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--instances)
                INSTANCE_FOLDER="$2"
                shift 2
                ;;
            -o|--output)
                RESULTS_FOLDER="$2"
                shift 2
                ;;
            -l|--license)
                GUROBI_LICENSE="$2"
                shift 2
                ;;
            -d|--docker)
                DOCKER_IMAGE="$2"
                shift 2
                ;;
            -p|--platform)
                DOCKER_PLATFORM="$2"
                shift 2
                ;;
            -s|--sleep)
                SLEEP_DURATION="$2"
                shift 2
                ;;
            --initial-sample)
                INITIAL_SAMPLE="$2"
                shift 2
                ;;
            --initial-sample-algorithm)
                INITIAL_SAMPLE_ALGORITHM="$2"
                shift 2
                ;;
            --initial-sample-algorithm-timelimit)
                INITIAL_SAMPLE_ALGORITHM_TIMELIMIT="$2"
                shift 2
                ;;
            --samplns-timelimit)
                SAMPLNS_TIMELIMIT="$2"
                shift 2
                ;;
            --samplns-max-iterations)
                SAMPLNS_MAX_ITERATIONS="$2"
                shift 2
                ;;
            --samplns-iteration-timelimit)
                SAMPLNS_ITERATION_TIMELIMIT="$2"
                shift 2
                ;;
            --cds-iteration-timelimit)
                CDS_ITERATION_TIMELIMIT="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                echo "❌ Unknown option: $1" >&2
                show_help >&2
                exit 1
                ;;
        esac
    done
}

# Validate prerequisites
validate_prerequisites() {
    echo "🔍 Validating prerequisites..."

    # Check if Docker can be run
    if ! docker info >/dev/null 2>&1; then
        echo "❌ Error: Docker does not seem to be running or is not installed."
        exit 1
    fi

    # Check if Docker image exists
    if ! docker image inspect "$DOCKER_IMAGE" >/dev/null 2>&1; then
        echo "❌ Error: Docker image '$DOCKER_IMAGE' not found!"
        echo "   Please build it with: docker build --platform $DOCKER_PLATFORM -t $DOCKER_IMAGE ."
        exit 1
    fi

    if [[ ! -f "$GUROBI_LICENSE" ]]; then
        echo "❌ Error: Gurobi license file not found at '$GUROBI_LICENSE'"
        echo "   Please place your Docker-compatible Gurobi license file (WLS) in the specified location."
        exit 1
    fi

    if [[ ! -d "$INSTANCE_FOLDER" ]]; then
        echo "❌ Error: Instance directory '$INSTANCE_FOLDER' not found!"
        echo "   Create a folder named '$INSTANCE_FOLDER' and move all the instances you want to solve in it."
        echo "   Supported formats: .xml (FeatJAR) and .dimacs (DIMACS)."
        exit 1
    fi

    # Validate initial sample file if provided
    if [[ -n "$INITIAL_SAMPLE" && ! -f "$INITIAL_SAMPLE" ]]; then
        echo "❌ Error: Initial sample file '$INITIAL_SAMPLE' not found!"
        exit 1
    fi

    # Validate that either initial sample or algorithm is specified
    if [[ -z "$INITIAL_SAMPLE" && -z "$INITIAL_SAMPLE_ALGORITHM" ]]; then
        echo "❌ Error: Either --initial-sample or --initial-sample-algorithm must be specified!"
        exit 1
    fi

    echo "✅ Prerequisites validated"
}

# Check for instances
check_instances() {
    local count
    count=$(find -L "$INSTANCE_FOLDER" -type f \( -name '*.xml' -o -name '*.dimacs' \) 2>/dev/null | wc -l)
    if [[ "$count" -eq 0 ]]; then
        echo "❌ No .xml or .dimacs files found in '$INSTANCE_FOLDER'"
        exit 1
    fi
    echo "📊 Found $count instance(s) to process"
}

# Build SampLNS arguments
build_samplns_args() {
    local args=""
    
    if [[ -n "$INITIAL_SAMPLE" ]]; then
        args="$args --initial-sample /initial_sample/$(basename "$INITIAL_SAMPLE")"
    else
        args="$args --initial-sample-algorithm $INITIAL_SAMPLE_ALGORITHM"
        args="$args --initial-sample-algorithm-timelimit $INITIAL_SAMPLE_ALGORITHM_TIMELIMIT"
    fi
    
    args="$args --samplns-timelimit $SAMPLNS_TIMELIMIT"
    
    [[ -n "$SAMPLNS_MAX_ITERATIONS" ]] && args="$args --samplns-max-iterations $SAMPLNS_MAX_ITERATIONS"
    [[ -n "$SAMPLNS_ITERATION_TIMELIMIT" ]] && args="$args --samplns-iteration-timelimit $SAMPLNS_ITERATION_TIMELIMIT"
    [[ -n "$CDS_ITERATION_TIMELIMIT" ]] && args="$args --cds-iteration-timelimit $CDS_ITERATION_TIMELIMIT"
    
    echo "$args"
}
# Helper: portable absolute path (works even if realpath isn't available)
to_abs() {
    if command -v realpath >/dev/null 2>&1; then
        realpath -m "$1"
    else
        # Use command substitution to concatenate the directory and basename
        echo "$(cd "$(dirname "$1")" && pwd -P)/$(basename "$1")"
    fi
}


# Process all instances (recursively, mirroring subfolders in results)
process_instances() {
    local processed=0
    local any_failed=0
    local samplns_args; samplns_args="$(build_samplns_args)"

    # Absolute paths for reliable docker -v mounts
    local abs_instances; abs_instances="$(to_abs "$INSTANCE_FOLDER")"
    local abs_results;   abs_results="$(to_abs "$RESULTS_FOLDER")"
    local abs_license;   abs_license="$(to_abs "$GUROBI_LICENSE")"

    # Base docker volumes
    local docker_volumes="-v $abs_license:/opt/gurobi/gurobi.lic:ro -v $abs_instances:/instances -v $abs_results:/results"
    if [[ -n "$INITIAL_SAMPLE" ]]; then
        local abs_init_dir; abs_init_dir="$(to_abs "$(dirname "$INITIAL_SAMPLE")")"
        docker_volumes="$docker_volumes -v $abs_init_dir:/initial_sample"
    fi

    # Use a TTY only if we're actually attached to one
    local docker_tty_flag=""
    if [[ -t 1 ]]; then
        docker_tty_flag="-t"
    fi

    # Find all instances recursively; handle spaces/newlines with -print0
    while IFS= read -r -d '' instance_file; do
        # Path relative to INSTANCE_FOLDER (to mirror subfolders in results)
        local rel_path="${instance_file#"$abs_instances"/}"
        local rel_dir;    rel_dir="$(dirname "$rel_path")"
        local base_name;  base_name="$(basename "$rel_path")"

        # Create output dir and file (mirroring subfolders)
        local output_dir="$abs_results/$rel_dir"
        local output_file="$output_dir/${base_name%.*}.json"
        mkdir -p "$output_dir"

        ((processed++))
        echo "🔄 Processing [$processed]: $rel_path"
        echo "   Output: ${output_file#"$abs_results/"}"

        # Container paths
        local container_input="/instances/$rel_path"
        local container_output="/results/$rel_dir/${base_name%.*}.json"

        # Run solver in Docker (no -i; add -t only if TTY)
        if docker run --platform "$DOCKER_PLATFORM" --rm $docker_tty_flag \
            $docker_volumes \
            "$DOCKER_IMAGE" \
            --file "$container_input" \
            --output "$container_output" \
            $samplns_args; then
            echo "✅ Completed: $rel_path"
        else
            echo "❌ Failed: $rel_path"
            any_failed=1
        fi

        echo "⏳ Sleeping for ${SLEEP_DURATION}s to prevent license conflicts..."
        sleep "$SLEEP_DURATION"
        echo
    done < <(find -L "$abs_instances" -type f \( -name '*.xml' -o -name '*.dimacs' \) -print0)

    echo "📈 Processed $processed instance(s)"
    return $any_failed
}


# Main execution
main() {
    parse_arguments "$@"
    
    echo "🚀 Starting SampLNS batch processing..."
    echo
    
    # Create results directory
    mkdir -p "$RESULTS_FOLDER"
    
    validate_prerequisites
    check_instances
    
    echo
    echo "⚙️  Configuration:"
    echo "   Instances: $INSTANCE_FOLDER"
    echo "   Results:   $RESULTS_FOLDER"
    echo "   License:   $GUROBI_LICENSE"
    echo "   Docker:    $DOCKER_IMAGE ($DOCKER_PLATFORM)"
    echo "   Sleep:     ${SLEEP_DURATION}s between solves"
    if [[ -n "$INITIAL_SAMPLE" ]]; then
        echo "   Initial Sample: $INITIAL_SAMPLE"
    else
        echo "   Initial Algorithm: $INITIAL_SAMPLE_ALGORITHM (${INITIAL_SAMPLE_ALGORITHM_TIMELIMIT}s)"
    fi
    echo "   SampLNS Timelimit: ${SAMPLNS_TIMELIMIT}s"
    [[ -n "$SAMPLNS_MAX_ITERATIONS" ]] && echo "   Max Iterations: $SAMPLNS_MAX_ITERATIONS"
    [[ -n "$SAMPLNS_ITERATION_TIMELIMIT" ]] && echo "   Iteration Timelimit: ${SAMPLNS_ITERATION_TIMELIMIT}s"
    [[ -n "$CDS_ITERATION_TIMELIMIT" ]] && echo "   CDS Timelimit: ${CDS_ITERATION_TIMELIMIT}s"
    echo
    
    if process_instances; then
        echo "✅ All instances processed successfully!"
    else
        echo "❌ Some instances failed to process."
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
