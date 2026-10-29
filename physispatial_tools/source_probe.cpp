// Validation driver only. Calls ORIGINAL functions; not a replacement simulator.
#include <cmath>
#include <fstream>
#include <iomanip>
#include <set>
#include <omp.h>
#include "core/PhysiCell.h"
#include "modules/PhysiCell_standard_modules.h"
#include "custom_modules/custom.h"
int main(int argc,char** argv) {
    if(argc!=3 || !PhysiCell::load_PhysiCell_config_file(argv[1])) return 2;
    omp_set_num_threads(1);
    setup_microenvironment();
    create_cell_types(); // Parses the real Boolean definitions, but allocates no tissue population.
    int drug=BioFVM::microenvironment.find_density_index("drug_A");
    if(drug<0) return 3;
    auto positions=read_cells_positions(PhysiCell::parameters.strings("blood_source_file"),'\t',true);
    std::set<int> ids;
    for(auto p:positions) ids.insert(BioFVM::microenvironment.voxel_index((int)p[0],(int)p[1],(int)p[2]));
    int before=0,after=0; double error=0;
    double requested=PhysiCell::parameters.doubles("drug_conc");
    for(int i:ids) before+=BioFVM::microenvironment.get_substrate_dirichlet_activation(drug,i);
    // Direct function-level activation test, NOT a time-advanced production trajectory.
    change_dirichlet_nodes();
    BioFVM::microenvironment.apply_dirichlet_conditions();
    for(int i:ids) {
        after+=BioFVM::microenvironment.get_substrate_dirichlet_activation(drug,i);
        error=std::max(error,std::abs(BioFVM::microenvironment.density_vector(i)[drug]-requested));
    }
    double radius=-1; size_t generated=0;
    #ifdef PHYSISPATIAL_SPHERE
    radius=PhysiCell::parameters.doubles("tumor_radius");
    auto generated_positions=create_cell_sphere_positions(PhysiCell::cell_defaults.phenotype.geometry.radius,radius);
    generated=generated_positions.size();
    #endif
    BioFVM::microenvironment.write_to_matlab("output/source_probe_microenvironment.mat");
    std::ofstream out(argv[2]);out<<std::setprecision(17);
    out<<"{\"D\":"<<BioFVM::microenvironment.diffusion_coefficients[drug]
       <<",\"C\":"<<requested<<",\"unique_prescribed_source_voxels\":"<<ids.size()
       <<",\"drug_active_sources_before\":"<<before<<",\"drug_active_sources_after\":"<<after
       <<",\"source_concentration_max_error\":"<<error
       <<",\"mesh_x\":"<<BioFVM::microenvironment.mesh.x_coordinates.size()
       <<",\"mesh_y\":"<<BioFVM::microenvironment.mesh.y_coordinates.size()
       <<",\"mesh_z\":"<<BioFVM::microenvironment.mesh.z_coordinates.size()
       <<",\"sphere_radius\":"<<radius<<",\"original_sphere_generator_positions\":"<<generated
       <<",\"full_tissue_initialized\":false,\"activation_invoked_directly_for_unit_test\":true}";
    return error>std::max(1e-20,std::abs(requested)*1e-12) || before!=0 || after!=(int)ids.size();
}
