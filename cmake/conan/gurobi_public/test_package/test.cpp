#include <gurobi_c++.h>

int main() {
	try {
		GRBEnv env;
		GRBModel model(env);
		model.optimize();
	} catch(GRBException& e) {
		std::cerr << "Gurobi exception: " << e.getMessage() << std::endl;
		std::cerr << "This error is probably license-related and should not stop the package to install successfully." << std::endl;
		return 0;
	}
	return 0;
}

