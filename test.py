import pyafl
import json
from Fuzzer import Fuzzer


path = "conf.json"

fuzzer = Fuzzer(path)

# fuzzer.print_test_cases()
# fuzzer.get_test_case_detail(1)
test_cases = fuzzer.get_init_test_cases()


# pyafl.pre_run_target(100)
messages, responses = fuzzer.run_target(test_cases[0])
fuzzer.fuzz_one_profile()
# fuzzer.profile_run_target(test_cases[0])


# fuzzer.calibrate_case(test_cases[0])  


# print(len(messages))
# print(len(responses))
# fuzzer.mr_log(messages, responses)

# fuzzer.save_pcap(messages,responses)


fuzzer.perform_dry_run()

fuzzer.fuzz()

fuzzer.clear()
