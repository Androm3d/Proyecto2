import os
import subprocess
import argparse
import logging
import pandas as pd
import matplotlib.pyplot as plt
import random
import time
from itertools import combinations


def create_directories():
    directories = [
        'results/real', 'results/virtual', 'datasets/real', 'datasets/virtual', 'bin', 'results', 'logs'
    ]
    types = ['bruteForce', 'MinHash', 'LSHbase', 'bucketing', 'forest']
    for directory in directories:
        if 'results/' in directory:
            for t in types:
                os.makedirs(os.path.join(directory, t), exist_ok=True)
        else:
            os.makedirs(directory, exist_ok=True)


# Set up logging
def setup_logging():
    logging.basicConfig(filename='logs/experiment.log',
                        level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        filemode='w')


def run_corpus_mode(executable_path,
                    dataset_path,
                    output_dir,
                    k=None,
                    t=None,
                    b=None,
                    thr=None):
    """Run corpus mode experiment"""
    cmd = [executable_path, dataset_path]
    
    # Generate base filename parts based on provided parameters
    param_parts = []
    if k is not None:
        param_parts.append(f"k{k}")
    if t is not None:
        param_parts.append(f"t{t}")
    if b is not None:
        param_parts.append(f"b{b}")
    if thr is not None:
        param_parts.append(f"threshold{thr}")
    
    # Determine algorithm type from executable path
    if 'BruteForce' in executable_path:
        algo_type = 'bruteForce'
    elif 'MinHash' in executable_path:
        algo_type = 'MinHash'
    elif 'LSHbase' in executable_path:
        algo_type = 'LSHbase'
    elif 'LSHbucketing' in executable_path:
        algo_type = 'bucketing'
    elif 'LSHforest' in executable_path:
        algo_type = 'forest'
    else:
        algo_type = 'unknown'

    # Handle specific parameter requirements for LSH bucketing and forest
    if 'LSHbucketing' in executable_path or 'LSHforest' in executable_path:
        if k is None or t is None or b is None or thr is None:
            logging.error(
                f"Error: {executable_path} requires k, t, b, and thr parameters."
            )
            return {
                'dataset': dataset_path,
                'output': f"Error: {executable_path} requires k, t, b, and thr parameters.",
                'runtime': None,
                'status': 'error'
            }

    # Add parameters if provided for other executables
    if k is not None:
        cmd.append(str(k))
    if t is not None:
        cmd.append(str(t))
    if b is not None:
        cmd.append(str(b))
    if thr is not None:
        cmd.append(str(thr))

    try:
        start_time = time.time()
        # Execute the command
        print(cmd)
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        end_time = time.time()

        # Log the run
        logging.info(
            f"Successfully ran corpus mode {executable_path} on {dataset_path}"
        )

        # Get output CSV files
        similarity_csv = os.path.join(output_dir, f"{algo_type}/{algo_type}Similarities_{'_'.join(param_parts)}.csv")
        times_csv = os.path.join(output_dir, f"{algo_type}/{algo_type}Times_{'_'.join(param_parts)}.csv")

        print(f"Output CSV files: {similarity_csv}, {times_csv}")

        return {
            'dataset': dataset_path,
            'similarity_csv': similarity_csv,
            'times_csv': times_csv,
            'runtime': end_time - start_time,
            'status': 'success',
            'method': algo_type,
            'k': k,
            't': t,
            'b': b,
            'thr': thr
        }
    except subprocess.CalledProcessError as e:
        logging.error(
            f"Error running corpus mode {executable_path}: {e}"
        )
        return {
            'dataset': dataset_path,
            'output': e.stderr,
            'runtime': None,
            'status': 'error',
            'method': algo_type,
            'k': k,
            't': t,
            'b': b,
            'thr': thr
        }


def parse_csv_results(result):
    """Parse results from CSV files instead of output"""
    if result['status'] == 'error':
        return {
            'dataset': result['dataset'],
            'similar_pairs': [],
            'index_build_time': None,
            'query_time': None,
            'total_runtime': result['runtime'],
            'status': result['status'],
            'method': result['method'],
            'k': result['k'],
            't': result['t'],
            'b': result['b'],
            'thr': result['thr']
        }

    similar_pairs = []
    index_build_time = None
    query_time = None

    # Parse similarity CSV if it exists
    try:
        print(result['similarity_csv'])
        if os.path.exists(result['similarity_csv']):
            similarity_df = pd.read_csv(result['similarity_csv'])
            # Extract document pairs
            if not similarity_df.empty:
                # Assuming the CSV has columns for doc1, doc2, and similarity
                for _, row in similarity_df.iterrows():
                    doc1 = row["Doc1"] if len(row) > 0 else None
                    doc2 = row["Doc2"] if len(row) > 1 else None
                    similarity = row["Sim%"] if len(row) > 2 else None
                    if doc1 is not None and doc2 is not None:
                        similar_pairs.append((str(doc1), str(doc2)))
            else:
                logging.error(f"No similar pairs found for {result['method']}")
        else:
            logging.error(f"Similarity CSV not found for {result['method']}")
    except Exception as e:
        logging.error(f"Error parsing similarity CSV: {e}")

    # Parse times CSV if it exists
    try:
        if os.path.exists(result['times_csv']):
            times_df = pd.read_csv(result['times_csv'])
            # Extract timing information
            if not times_df.empty:
                # Assuming the CSV has columns for task and time
                for _, row in times_df.iterrows():
                    task = row["Operation"] if len(row) > 0 else ""
                    time_value = row["Time(ms)"] if len(row) > 1 else None
                    
                    if isinstance(task, str):
                        if "index build" in task.lower() and time_value is not None:
                            index_build_time = float(time_value)
                        elif "query" in task.lower() and time_value is not None:
                            query_time = float(time_value)
                        elif "time" in task.lower() and time_value is not None:
                            total_runtime = float(time_value)
                    else:
                        logging.error(f"Invalid task name in times CSV: {task}")
            else:
                logging.error(f"No timing information found for {result['method']}")
        else:
            logging.error(f"Times CSV not found for {result['method']}")
    except Exception as e:
        logging.error(f"Error parsing times CSV: {e}")

    return {
        'dataset': result['dataset'],
        'similar_pairs': similar_pairs,
        'index_build_time': index_build_time,
        'query_time': query_time,
        'total_runtime': total_runtime,
        'status': result['status'],
        'method': result['method'],
        'k': result['k'],
        't': result['t'],
        'b': result['b'],
        'thr': result['thr']
    }


def run_parameter_experiment(bin, dataset_dir, output_dir, param_to_vary, 
                            base_k=5, base_t=500, base_b=50, base_thr=0.3):
    """Run experiments varying one parameter while fixing others"""
    results = []
    
    # Convert base_b from percentage to actual value based on base_t
    base_b_value = int(base_t * (base_b / 100.0)) if base_b is not None else None
    
    logging.info(f"Running experiment varying {param_to_vary}")
    
    for exec_name, exec_path in bin.items():
        logging.info(f"Running {exec_name} with varying {param_to_vary}")
        
        # Define which parameters to use based on algorithm type
        uses_t = exec_name != 'brute_force'
        uses_b = 'lsh' in exec_name
        uses_thr = exec_name not in ['minhash', 'lsh_basic', 'brute_force']
        
        # Set parameter values for this algorithm
        k_val = base_k
        t_val = base_t if uses_t else None
        b_val = base_b_value if uses_b else None
        thr_val = base_thr if uses_thr else None
        
        # Get parameter values to vary
        if param_to_vary == 'k':
            values_to_try = [3, 5, 7, 9]
        elif param_to_vary == 't' and uses_t:
            values_to_try = [300, 500, 700]
        elif param_to_vary == 'b' and uses_b:
            # Convert percentage to actual values
            values_to_try = [int(base_t * (pct / 100.0)) for pct in [30, 50, 70]]
        elif param_to_vary == 'thr' and uses_thr:
            values_to_try = [0.4, 0.5, 0.6]
        else:
            values_to_try = []  # Skip if parameter doesn't apply to this algorithm
            
        # Run experiments with varying parameter
        for val in values_to_try:
            # Set the parameter to vary
            if param_to_vary == 'k':
                k_val = val
            elif param_to_vary == 't':
                t_val = val
                # Update b since it depends on t
                if uses_b:
                    b_val = int(val * (base_b / 100.0))
            elif param_to_vary == 'b':
                b_val = val
            elif param_to_vary == 'thr':
                thr_val = val
                
            # Run with current parameter values
            result = run_corpus_mode(exec_path, dataset_dir, output_dir, 
                                    k_val, t_val, b_val, thr_val)
            
            # Parse results
            parsed_result = parse_csv_results(result)
            parsed_result['similar_pairs_count'] = len(parsed_result['similar_pairs'])
            parsed_result['varied_param'] = param_to_vary
            parsed_result['varied_value'] = val
            
            results.append(parsed_result)
    
    # Create DataFrame with results
    df = pd.DataFrame(results)
    
    # Save results to CSV
    results_file = os.path.join(output_dir, f"results_vary_{param_to_vary}.csv")
    df.to_csv(results_file, index=False)
    
    return df


def prepare_datasets(mode, num_docs):
    """Prepare datasets based on mode"""
    logging.info(f"Preparing {mode} datasets with {num_docs} documents...")

    # if datasets already exist, erase them
    if len(os.listdir(f'datasets/{mode}/')) > 0:
        logging.info("Deleting existing datasets...")
        for file in os.listdir(f'datasets/{mode}/'):
            os.remove(f'datasets/{mode}/{file}')

    if mode == 'real':
        gen_k = None
        cmd = ["./bin/exp1_genRandPerm", str(num_docs)]
    else:  # virtual mode
        gen_k = str(random.randint(4, 10))
        cmd = ["./bin/exp2_genRandShingles", gen_k, str(num_docs)]

    try:
        start_time = time.time()
        result = subprocess.run(cmd,
                                capture_output=True,
                                text=True,
                                check=True)
        end_time = time.time()

        # Log the run
        logging.info(
            f"Successfully ran dataset generation and created dataset containing {num_docs} documents"
        )

        return {
            "output": result.stdout,
            "runtime": end_time - start_time,
            "status": "success",
        }
    except subprocess.CalledProcessError as e:
        logging.error(f"Error preparing datasets: {e}")
        return {
            "dataset": None,
            "output": e.stderr,
            "runtime": None,
            "status": "error",
        }
    

def plot_parameter_comparison(results_df, param_name, metric_name, output_dir):
    """
    Plot performance comparison for varying parameter values
    
    Args:
        results_df: DataFrame with experiment results
        param_name: Parameter that was varied ('k', 't', 'b', 'thr')
        metric_name: Metric to plot ('total_runtime', 'similar_pairs_count', etc.)
        output_dir: Directory to save the plot
    """
    plt.figure(figsize=(10, 6))
    
    # Get algorithms present in results
    algorithms = results_df['method'].unique()
    
    for algo in algorithms:
        algo_df = results_df[results_df['method'] == algo]
        if not algo_df.empty:
            # Sort by parameter value for proper line plotting
            algo_df = algo_df.sort_values(by='varied_value')
            plt.plot(algo_df['varied_value'], algo_df[metric_name], marker='o', label=algo)
    
    # Set labels and title
    param_labels = {
        'k': 'Shingle Size (k)',
        't': 'Number of Hash Functions (t)',
        'b': 'Number of Bands (b)',
        'thr': 'Similarity Threshold'
    }
    
    metric_labels = {
        'total_runtime': 'Total Runtime (ms)',
        'index_build_time': 'Index Build Time (ms)',
        'query_time': 'Query Time (ms)',
        'similar_pairs_count': 'Number of Similar Pairs'
    }
    
    plt.xlabel(param_labels.get(param_name, param_name))
    plt.ylabel(metric_labels.get(metric_name, metric_name))
    plt.title(f'Effect of {param_labels.get(param_name, param_name)} on {metric_labels.get(metric_name, metric_name)}')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    # Save the plot
    plot_file = os.path.join(output_dir, f'plot_{param_name}_{metric_name}.png')
    plt.savefig(plot_file)
    plt.close()
    
    logging.info(f"Plot saved to {plot_file}")
    return plot_file


def plot_algorithm_comparison(results_dfs, metric_name, output_dir):
    """
    Plot performance comparison across all algorithms for all parameter experiments
    
    Args:
        results_dfs: List of DataFrames with results from different parameter experiments
        metric_name: Metric to plot ('total_runtime', 'similar_pairs_count', etc.)
        output_dir: Directory to save the plot
    """
    plt.figure(figsize=(12, 8))
    
    # Combine results from all parameter experiments
    combined_df = pd.concat(results_dfs)
    
    # Group by algorithm and calculate mean metric value
    algo_summary = combined_df.groupby('method')[metric_name].mean().reset_index()
    
    # Sort by metric value for better visualization
    algo_summary = algo_summary.sort_values(by=metric_name)
    
    # Create bar plot
    bars = plt.bar(algo_summary['method'], algo_summary[metric_name])
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height:.2f}', ha='center', va='bottom')
    
    metric_labels = {
        'total_runtime': 'Average Runtime (ms)',
        'index_build_time': 'Average Index Build Time (ms)',
        'query_time': 'Average Query Time (ms)',
        'similar_pairs_count': 'Average Number of Similar Pairs'
    }
    
    plt.ylabel(metric_labels.get(metric_name, metric_name))
    plt.title(f'Algorithm Comparison: {metric_labels.get(metric_name, metric_name)}')
    plt.xticks(rotation=45)
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    # Save the plot
    plot_file = os.path.join(output_dir, f'algorithm_comparison_{metric_name}.png')
    plt.savefig(plot_file)
    plt.close()
    
    logging.info(f"Plot saved to {plot_file}")
    return plot_file


def compare_accuracy(results_dfs, output_dir):
    """
    Compare accuracy of algorithms against brute force (ground truth)
    
    Args:
        results_dfs: List of DataFrames with results from different parameter experiments
        output_dir: Directory to save the plot
    """
    # Find all brute force results to use as ground truth
    brute_force_results = []
    for df in results_dfs:
        bf_df = df[df['method'] == 'bruteForce']
        if not bf_df.empty:
            brute_force_results.append(bf_df)
    
    if not brute_force_results:
        logging.error("No brute force results found for accuracy comparison")
        return
    
    # Combine all brute force results
    combined_bf = pd.concat(brute_force_results)
    
    # Get a set of all similar pairs found by brute force (ground truth)
    ground_truth_pairs = set()
    for pairs in combined_bf['similar_pairs']:
        if isinstance(pairs, list):
            ground_truth_pairs.update(tuple(sorted(pair)) for pair in pairs)
    
    # Calculate precision and recall for each algorithm
    accuracy_results = []
    
    for df in results_dfs:
        for _, row in df.iterrows():
            if row['method'] != 'bruteForce':
                algo_pairs = set()
                if isinstance(row['similar_pairs'], list):
                    algo_pairs = set(tuple(sorted(pair)) for pair in row['similar_pairs'])
                
                # Calculate precision and recall if ground truth has pairs
                if ground_truth_pairs:
                    true_positives = len(algo_pairs.intersection(ground_truth_pairs))
                    precision = true_positives / len(algo_pairs) if algo_pairs else 0
                    recall = true_positives / len(ground_truth_pairs)
                    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
                else:
                    precision, recall, f1 = 0, 0, 0
                
                accuracy_results.append({
                    'method': row['method'],
                    'varied_param': row['varied_param'],
                    'varied_value': row['varied_value'],
                    'precision': precision,
                    'recall': recall,
                    'f1_score': f1
                })
    
    # Create DataFrame for plotting
    accuracy_df = pd.DataFrame(accuracy_results)
    
    # Plot f1 scores for each algorithm across different parameter values
    for param in accuracy_df['varied_param'].unique():
        param_df = accuracy_df[accuracy_df['varied_param'] == param]
        
        plt.figure(figsize=(10, 6))
        
        for algo in param_df['method'].unique():
            algo_df = param_df[param_df['method'] == algo]
            if not algo_df.empty:
                algo_df = algo_df.sort_values(by='varied_value')
                plt.plot(algo_df['varied_value'], algo_df['f1_score'], marker='o', label=algo)
        
        param_labels = {
            'k': 'Shingle Size (k)',
            't': 'Number of Hash Functions (t)',
            'b': 'Number of Bands (b)',
            'thr': 'Similarity Threshold'
        }
        
        plt.xlabel(param_labels.get(param, param))
        plt.ylabel('F1 Score')
        plt.title(f'F1 Score vs {param_labels.get(param, param)}')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.ylim(0, 1.05)
        
        # Save the plot
        plot_file = os.path.join(output_dir, f'accuracy_{param}.png')
        plt.savefig(plot_file)
        plt.close()
        
        logging.info(f"Accuracy plot saved to {plot_file}")
    
    return accuracy_df


def analyze_and_visualize_results(mode, experiment_types=['vary_k', 'vary_t', 'vary_b', 'vary_thr']):
    """
    Analyze results from all experiments and generate visualization
    
    Args:
        mode: Dataset mode ('real' or 'virtual')
        experiment_types: List of experiment types to analyze
    """
    logging.info(f"Analyzing and visualizing results for {mode} mode")
    
    output_dir = os.path.join('results', mode)
    results_dfs = []
    
    # Load result CSVs
    for exp_type in experiment_types:
        param = exp_type.split('_')[1]
        results_file = os.path.join(output_dir, f"results_vary_{param}.csv")
        
        if os.path.exists(results_file):
            try:
                df = pd.read_csv(results_file)
                
                # Convert similar_pairs from string to actual lists if needed
                if 'similar_pairs' in df.columns and df['similar_pairs'].dtype == 'object':
                    df['similar_pairs'] = df['similar_pairs'].apply(eval)
                
                results_dfs.append(df)
                logging.info(f"Loaded results from {results_file}")
            except Exception as e:
                logging.error(f"Error loading results from {results_file}: {e}")
    
    if not results_dfs:
        logging.error("No result files found for analysis")
        return
    
    # Create visualization directory
    viz_dir = os.path.join(output_dir, 'visualizations')
    os.makedirs(viz_dir, exist_ok=True)
    
    # Generate runtime comparison plots for each parameter variation
    metrics = ['total_runtime', 'index_build_time', 'query_time', 'similar_pairs_count']
    
    for df in results_dfs:
        if not df.empty:
            param_name = df['varied_param'].iloc[0]
            
            for metric in metrics:
                if metric in df.columns:
                    plot_parameter_comparison(df, param_name, metric, viz_dir)
    
    # Generate algorithm comparison plots
    for metric in metrics:
        plot_algorithm_comparison(results_dfs, metric, viz_dir)
    
    # Compare accuracy against brute force
    accuracy_df = compare_accuracy(results_dfs, viz_dir)
    
    # Save summary report
    create_summary_report(results_dfs, accuracy_df, viz_dir)
    
    logging.info(f"Visualization completed. Results available in {viz_dir}")


def create_summary_report(results_dfs, accuracy_df, output_dir):
    """Create a summary report with key findings"""
    combined_df = pd.concat(results_dfs)
    
    # Group by method and calculate averages
    method_summary = combined_df.groupby('method').agg({
        'total_runtime': 'mean',
        'index_build_time': 'mean',
        'query_time': 'mean',
        'similar_pairs_count': 'mean'
    }).reset_index()
    
    # Find the fastest method overall
    fastest_method = method_summary.loc[method_summary['total_runtime'].idxmin()]['method']
    
    # Find the method that finds most similar pairs (after brute force)
    non_bf_summary = method_summary[method_summary['method'] != 'bruteForce']
    most_pairs_method = non_bf_summary.loc[non_bf_summary['similar_pairs_count'].idxmax()]['method'] if not non_bf_summary.empty else None
    
    # Calculate average F1 scores if accuracy data is available
    if accuracy_df is not None and not accuracy_df.empty:
        avg_accuracy = accuracy_df.groupby('method')['f1_score'].mean().reset_index()
        most_accurate_method = avg_accuracy.loc[avg_accuracy['f1_score'].idxmax()]['method']
    else:
        most_accurate_method = None
    
    # Create report
    with open(os.path.join(output_dir, 'summary_report.txt'), 'w') as f:
        f.write("# Document Similarity Methods Evaluation Summary\n\n")
        
        f.write("## Overall Performance\n")
        f.write(f"- Fastest method: {fastest_method}\n")
        if most_pairs_method:
            f.write(f"- Method finding most similar pairs: {most_pairs_method}\n")
        if most_accurate_method:
            f.write(f"- Most accurate method: {most_accurate_method}\n")
        
        f.write("\n## Method Comparison\n")
        method_summary['total_runtime'] = method_summary['total_runtime'].map('{:.2f}'.format)
        method_summary['similar_pairs_count'] = method_summary['similar_pairs_count'].map('{:.1f}'.format)
        f.write(method_summary.to_string(index=False))
        
        f.write("\n\n## Parameter Effects\n")
        for df in results_dfs:
            if not df.empty:
                param = df['varied_param'].iloc[0]
                f.write(f"\n### Effect of varying {param}\n")
                
                # Find optimal parameter value for each method
                for method in df['method'].unique():
                    method_df = df[df['method'] == method]
                    if not method_df.empty:
                        best_runtime_idx = method_df['total_runtime'].idxmin()
                        best_value = method_df.loc[best_runtime_idx]['varied_value']
                        f.write(f"- Best {param} value for {method}: {best_value}\n")
    
    logging.info(f"Summary report created at {os.path.join(output_dir, 'summary_report.txt')}")


def main():
    parser = argparse.ArgumentParser(
        description='Document Similarity Methods Evaluation')
    parser.add_argument('--mode',
                        choices=['real', 'virtual'],
                        required=True,
                        help='Dataset mode: real or virtual')
    parser.add_argument('--num_docs',
                        type=int,
                        default=300,
                        help='Number of documents to generate')
    parser.add_argument('--prepare_datasets',
                        action='store_true',
                        help='Prepare datasets before running experiments')
    parser.add_argument('--experiment_type',
                        choices=['vary_k', 'vary_t', 'vary_b', 'vary_thr', 'all', 'analyze_only'],
                        default='all',
                        help='Type of experiment to run')
    # Base parameter values
    parser.add_argument('--base_k',
                        type=int,
                        default=5,
                        help='Base value for k (shingle size)')
    parser.add_argument('--base_t',
                        type=int,
                        default=500,
                        help='Base value for t (number of hash functions)')
    parser.add_argument('--base_b',
                        type=int,
                        default=50,
                        help='Base value for b as percentage of t')
    parser.add_argument('--base_thr',
                        type=float,
                        default=0.5,
                        help='Base value for threshold')
    parser.add_argument('--visualize',
                        action='store_true',
                        help='Generate visualizations after experiments')

    args = parser.parse_args()

    create_directories()
    setup_logging()

    if args.prepare_datasets:
        result = prepare_datasets(args.mode, args.num_docs)
        if result['status'] == 'error':
            logging.error("Failed to prepare datasets. Exiting.")
            return

    bin = {
        'brute_force': './bin/jaccardBruteForce',
        'minhash': './bin/jaccardMinHash',
        'lsh_basic': './bin/jaccardLSHbase',
        'lsh_bucketing': './bin/jaccardLSHbucketing',
        'lsh_forest': './bin/jaccardLSHforest'
    }

    dataset_dir = os.path.join('datasets', args.mode)
    output_dir = os.path.join('results', args.mode)
    os.makedirs(output_dir, exist_ok=True)

    # Skip running experiments if analyze_only is specified
    if args.experiment_type != 'analyze_only':
        # Run experiments based on the specified type
        if args.experiment_type == 'vary_k' or args.experiment_type == 'all':
            logging.info("Running experiment varying k...")
            run_parameter_experiment(bin, dataset_dir, output_dir, 'k', 
                                    args.base_k, args.base_t, args.base_b, args.base_thr)
            
        if args.experiment_type == 'vary_t' or args.experiment_type == 'all':
            logging.info("Running experiment varying t...")
            run_parameter_experiment(bin, dataset_dir, output_dir, 't', 
                                    args.base_k, args.base_t, args.base_b, args.base_thr)
            
        if args.experiment_type == 'vary_b' or args.experiment_type == 'all':
            logging.info("Running experiment varying b...")
            run_parameter_experiment(bin, dataset_dir, output_dir, 'b', 
                                    args.base_k, args.base_t, args.base_b, args.base_thr)
            
        if args.experiment_type == 'vary_thr' or args.experiment_type == 'all':
            logging.info("Running experiment varying threshold...")
            run_parameter_experiment(bin, dataset_dir, output_dir, 'thr', 
                                    args.base_k, args.base_t, args.base_b, args.base_thr)

        logging.info("Experiments completed successfully.")
    
    # Generate visualizations if requested or if analyze_only
    if args.visualize or args.experiment_type == 'analyze_only':
        logging.info("Generating visualizations...")
        
        # Determine which experiment types to analyze
        if args.experiment_type == 'all' or args.experiment_type == 'analyze_only':
            experiment_types = ['vary_k', 'vary_t', 'vary_b', 'vary_thr']
        else:
            experiment_types = [args.experiment_type]
        
        analyze_and_visualize_results(args.mode, experiment_types)
        logging.info("Visualization completed.")

if __name__ == "__main__":
    main()