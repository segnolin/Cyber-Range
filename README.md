# Cyber Range

Cyber range is macOS automated evidence collection and detection system for companies to assess red team attacks.

## Demo Video

- [Cyber Range Test (with CC_FruitFly.B) 200804](https://www.youtube.com/watch?v=1OqosE6Mlag)
- [Cyber Range Test (with GDoor) 200813](https://www.youtube.com/watch?v=Im991W4UdRQ)

## Getting Started

Simply cloning the project.

```
git clone https://github.com/segnolin/Cyber-Range.git
```

### Prerequisites

- Python 3.6+
- VMware Fusion 11+

### Environment Setup

In order to successfully run the cyber range, you need to setup a macOS 10.15 environment using VMware Fusion.

- [Setup Manual](https://hackmd.io/9H8eszwjSO6qNJgl4Nij-g)

### Creating Task File

The following are the properties of task file:
```
{
  "id": string (identifier for the task),
  "name": string (name or alias for the task),
  "vm": string (absoluate path to the .vmx file),
  "collector": string (absolute path to macOSCollector porject root),
  "monitor": string (absolute path to macOSMonitor project root),
  "snapshot": string (name of target snapshot),
  "user_name": string (user permission account name),
  "user_password": string (user permission account password),
  "root_password": string (root permission password),
  "files": [ (file mapping)
    {
      "source": string (host's absolute path to the source file),
      "target": string (guest's absolute path to the target file)
    },
    ...
  ],
  "commands": [ (series of commands execution)
    {
      "command": string (command to execute),
      "permission": string ("root" or "user" permission)
    },
    ...
  ],
  "time": string (number in string to indicate the monitoring duration)
}
```

For more task file example, you can check inside `./example` folder

### Usage

```
python3 automation.py --task path_to_task_file
```

## Advanced Usage

### Adding Detection to Rule File

In `rule.json`, you can add the detection rule to each technique.
The following properties are allowed to do so:

```
{
  "id": ...,
  "name": ...,
  "detection": [
    {
      "evidence": string (name of evidence),
      "tool": string (name of tool),
      "source": array[string] (relative path of detecing file, and wildcard is avaiable),
      "pattern": [
        {
          "key": string,
          "has": array[string]
        },
        {
          "and": [ (and condition)
            {
              "key": string,
              "has": array[string]
            },
            {
              "key": string,
              "has": array[string]
            }
          ]
        }
      ]
    }
  ]
},
...
```

### Filtering Artifacts

In `filter.json`, you can filter the duplicated entry during before & after comparison.
The following properties are allowed to do so:
```
[
  {
    "path": string (relative path to the artifact file, and wildcard is available),
    "ignore": array[string] (the key to ignore)
  },
  ...
]
```
