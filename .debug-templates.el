(dap-register-debug-template
  "Python :: Run pytest - from anywhere"
  (list :type "python"
        ;; in place of running the whole test, a specific test can be set here
        ;; eg: :args "test/test_process_config.py::test_process_toml"
        :args nil
        :cwd "${workspaceFolder}"
        ;; if this is nil it will append the buffer file name, which stops pytest from running all tests
        :program ""
        :module "pytest"
        :request "launch"
        ;; https://code.visualstudio.com/docs/python/testing#_pytest-configuration-settings for more info
        :environment-variables '(("PYTEST_ADDOPTS" . "--no-cov"))
        :name "Python :: Run pytest - from anywhere"))
