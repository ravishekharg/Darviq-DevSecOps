package kubernetes

import future.keywords.if
import future.keywords.in

deny[msg] if {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    not container.resources.limits.cpu
    msg := sprintf(
        "Container '%v' in Deployment '%v' must set CPU limits",
        [container.name, input.metadata.name]
    )
}

deny[msg] if {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    not container.resources.limits.memory
    msg := sprintf(
        "Container '%v' in Deployment '%v' must set memory limits",
        [container.name, input.metadata.name]
    )
}

deny[msg] if {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    not container.resources.requests.cpu
    msg := sprintf(
        "Container '%v' in Deployment '%v' must set CPU requests",
        [container.name, input.metadata.name]
    )
}