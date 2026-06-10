package kubernetes

import future.keywords.if
import future.keywords.in

deny[msg] if {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    container.securityContext.privileged == true
    msg := sprintf(
        "Container '%v' in Deployment '%v' must not run as privileged",
        [container.name, input.metadata.name]
    )
}

deny[msg] if {
    input.kind == "Deployment"
    input.spec.template.spec.hostPID == true
    msg := sprintf(
        "Deployment '%v' must not share the host PID namespace",
        [input.metadata.name]
    )
}

deny[msg] if {
    input.kind == "Deployment"
    input.spec.template.spec.hostNetwork == true
    msg := sprintf(
        "Deployment '%v' must not use host networking",
        [input.metadata.name]
    )
}