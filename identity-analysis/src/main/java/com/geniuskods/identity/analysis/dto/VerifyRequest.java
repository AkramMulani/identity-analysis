package com.geniuskods.identity.analysis.dto;

import lombok.Data;

@Data
public class VerifyRequest {
    private String probeTemplate;
    private String candidateTemplate;
}