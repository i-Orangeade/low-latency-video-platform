#include <cstdlib>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    const std::string stream_id = argc > 1 ? argv[1] : "drone_001";
    const std::string input = argc > 2 ? argv[2] : "";
    const std::string url = "rtmp://127.0.0.1/live/" + stream_id;

    std::string command;
    if (input.empty()) {
        command =
            "ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=25 "
            "-f lavfi -i sine=frequency=1000:sample_rate=44100 "
            "-c:v libx264 -preset veryfast -tune zerolatency -g 50 -bf 0 "
            "-pix_fmt yuv420p -c:a aac -ar 44100 -b:a 96k -f flv " +
            url;
    } else {
        command =
            "ffmpeg -re -stream_loop -1 -i \"" + input +
            "\" -c:v libx264 -preset veryfast -tune zerolatency -g 50 -bf 0 "
            "-c:a aac -ar 44100 -b:a 96k -f flv " +
            url;
    }

    std::cout << "Pushing to " << url << std::endl;
    return std::system(command.c_str());
}
