#include <cstdlib>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    const std::string stream_id = argc > 1 ? argv[1] : "drone_001";
    const std::string api =
        "http://127.0.0.1:8000/api/streams/" + stream_id + "/status";
    const std::string command = "curl -s \"" + api + "\"";

    std::cout << "Querying stream status: " << api << std::endl;
    const int code = std::system(command.c_str());
    std::cout << std::endl;
    return code;
}
