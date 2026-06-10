package kubernetes

import future.keywords.if
import future.keywords.in

required_labels := {"app", "version", "team", "env"}

deny[msg] if {
    input.kind == "Deployment"
    label := required_labels[_]
    not input.metadata.labels[label]
    msg := sprintf(
        "Deployment '%v' is missing required label: '%v'",
        [input.metadata.name, label]
    )
}

deny[msg] if {
    input.kind == "Deployment"
    label := required_labels[_]
    not input.spec.template.metadata.labels[label]
    msg := sprintf(
        "Pod template in Deployment '%v' is missing required label: '%v'",
        [input.metadata.name, label]
    )
}